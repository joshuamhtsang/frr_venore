// SPDX-License-Identifier: GPL-2.0-or-later
/*
 * EIGRP Daemon Program.
 * Copyright (C) 2013-2014
 * Authors:
 *   Donnie Savage
 *   Jan Janovic
 *   Matej Perina
 *   Peter Orsag
 *   Peter Paluch
 */

#include <zebra.h>

#include "frrevent.h"
#include "vty.h"
#include "command.h"
#include "linklist.h"
#include "prefix.h"
#include "table.h"
#include "if.h"
#include "memory.h"
#include "stream.h"
#include "log.h"
#include "sockunion.h" /* for inet_aton () */
#include "zclient.h"
#include "plist.h"
#include "sockopt.h"
#include "keychain.h"
#include "libfrr.h"
#include "lib_errors.h"
#include "distribute.h"

#include "eigrpd/eigrp_structs.h"
#include "eigrpd/eigrpd.h"
#include "eigrpd/eigrp_interface.h"
#include "eigrpd/eigrp_zebra.h"
#include "eigrpd/eigrp_vty.h"
#include "eigrpd/eigrp_neighbor.h"
#include "eigrpd/eigrp_packet.h"
#include "eigrpd/eigrp_network.h"
#include "eigrpd/eigrp_topology.h"
#include "eigrpd/eigrp_filter.h"

DEFINE_MGROUP(EIGRPD, "eigrpd");

DEFINE_MTYPE_STATIC(EIGRPD, EIGRP_TOP, "EIGRP structure");

DEFINE_QOBJ_TYPE(eigrp);

static struct eigrp_master eigrp_master;

struct eigrp_master *eigrp_om;

extern struct in_addr router_id_zebra;

int eigrp_master_hash_cmp(const struct eigrp *a, const struct eigrp *b)
{
	return a->vrf_id - b->vrf_id;
}

uint32_t eigrp_master_hash_hash(const struct eigrp *a)
{
	return a->vrf_id;
}

/*
 * void eigrp_router_id_update(struct eigrp *eigrp)
 *
 * Description:
 * update routerid associated with this instance of EIGRP.
 * If the id changes, then call if_update for each interface
 * to resync the topology database with all neighbors
 *
 * Select the router ID based on these priorities:
 *   1. Statically assigned router ID is always the first choice.
 *   2. If there is no statically assigned router ID, then try to stick
 *      with the most recent value, since changing router ID's is very
 *      disruptive.
 *   3. Last choice: just go with whatever the zebra daemon recommends.
 *
 * Note:
 * router id for EIGRP is really just a 32 bit number. Cisco historically
 * displays it in dotted decimal notation, and will pickup an IP address
 * from an interface so it can be 'auto-configed" to a uniqe value
 *
 * This does not work for IPv6, and to make the code simpler, its
 * stored and processed internerall as a 32bit number
 */
void eigrp_router_id_update(struct eigrp *eigrp)
{
	struct vrf *vrf = vrf_lookup_by_id(eigrp->vrf_id);
	struct interface *ifp;
	struct in_addr router_id, router_id_old;

	router_id_old = eigrp->router_id;

	if (eigrp->router_id_static.s_addr != INADDR_ANY)
		router_id = eigrp->router_id_static;

	else if (eigrp->router_id.s_addr != INADDR_ANY)
		router_id = eigrp->router_id;

	else
		router_id = router_id_zebra;

	eigrp->router_id = router_id;
	if (router_id_old.s_addr != router_id.s_addr) {
		/* update eigrp_interface's */
		FOR_ALL_INTERFACES (vrf, ifp)
			eigrp_if_update(ifp);
	}
}

void eigrp_master_init(void)
{
	struct timeval tv;

	memset(&eigrp_master, 0, sizeof(eigrp_master));

	eigrp_om = &eigrp_master;
	eigrp_master_hash_init(&eigrp_om->eigrp);

	monotime(&tv);
	eigrp_om->start_time = tv.tv_sec;
}

/* Allocate new eigrp structure. */
static struct eigrp *eigrp_new(uint16_t as, vrf_id_t vrf_id)
{
	struct eigrp *eigrp = XCALLOC(MTYPE_EIGRP_TOP, sizeof(struct eigrp));

	/* init information relevant to peers */
	eigrp->vrf_id = vrf_id;
	eigrp->vrid = 0;
	eigrp->AS = as;
	eigrp->router_id.s_addr = INADDR_ANY;
	eigrp->router_id_static.s_addr = INADDR_ANY;
	eigrp->sequence_number = 1;

	/*Configure default K Values for EIGRP Process*/
	eigrp->k_values[0] = EIGRP_K1_DEFAULT;
	eigrp->k_values[1] = EIGRP_K2_DEFAULT;
	eigrp->k_values[2] = EIGRP_K3_DEFAULT;
	eigrp->k_values[3] = EIGRP_K4_DEFAULT;
	eigrp->k_values[4] = EIGRP_K5_DEFAULT;
	eigrp->k_values[5] = EIGRP_K6_DEFAULT;

	/* init internal data structures */
	eigrp_interface_hash_init(&eigrp->eifs);
	eigrp->passive_interface_default = EIGRP_IF_ACTIVE;
	eigrp->networks = eigrp_topology_new();

	eigrp->fd = eigrp_sock_init(vrf_lookup_by_id(vrf_id));

	if (eigrp->fd < 0) {
		flog_err_sys(
			EC_LIB_SOCKET,
			"%s: fatal error: eigrp_sock_init was unable to open a socket",
			__func__);
		exit(1);
	}

	eigrp->maxsndbuflen = getsockopt_so_sendbuf(eigrp->fd);

	eigrp->ibuf = stream_new(EIGRP_PACKET_MAX_LEN + 1);

	event_add_read(master, eigrp_read, eigrp, eigrp->fd, &eigrp->t_read);
	eigrp->oi_write_q = list_new();

	eigrp->topology_table = route_table_init();

	eigrp->neighbor_self = eigrp_nbr_new(NULL);
	eigrp->neighbor_self->src.s_addr = INADDR_ANY;

	eigrp->variance = EIGRP_VARIANCE_DEFAULT;
	eigrp->max_paths = EIGRP_MAX_PATHS_DEFAULT;

	eigrp->serno = 0;
	eigrp->serno_last_update = 0;
	eigrp->topology_changes_externalIPV4 = list_new();
	eigrp->topology_changes_internalIPV4 = list_new();

	eigrp->list[EIGRP_FILTER_IN] = NULL;
	eigrp->list[EIGRP_FILTER_OUT] = NULL;

	eigrp->prefix[EIGRP_FILTER_IN] = NULL;
	eigrp->prefix[EIGRP_FILTER_OUT] = NULL;

	eigrp->routemap[EIGRP_FILTER_IN] = NULL;
	eigrp->routemap[EIGRP_FILTER_OUT] = NULL;

	/* Distribute list install. */
	eigrp->distribute_ctx =
		distribute_list_ctx_create(vrf_lookup_by_id(eigrp->vrf_id));
	distribute_list_add_hook(eigrp->distribute_ctx,
				 eigrp_distribute_update);
	distribute_list_delete_hook(eigrp->distribute_ctx,
				    eigrp_distribute_update);

	/*
	  eigrp->if_rmap_ctx = if_rmap_ctx_create(eigrp->vrf_id);
	  if_rmap_hook_add (eigrp_if_rmap_update);
	  if_rmap_hook_delete (eigrp_if_rmap_update);
	*/
	QOBJ_REG(eigrp, eigrp);
	return eigrp;
}

struct eigrp *eigrp_get(uint16_t as, vrf_id_t vrf_id)
{
	struct eigrp *eigrp;

	eigrp = eigrp_lookup(vrf_id);
	if (eigrp == NULL) {
		eigrp = eigrp_new(as, vrf_id);
		eigrp_master_hash_add(&eigrp_om->eigrp, eigrp);
	}

	return eigrp;
}

/* Shut down the entire process */
void eigrp_terminate(void)
{
	struct eigrp *eigrp;

	/* shutdown already in progress */
	if (CHECK_FLAG(eigrp_om->options, EIGRP_MASTER_SHUTDOWN))
		return;

	SET_FLAG(eigrp_om->options, EIGRP_MASTER_SHUTDOWN);

	while (eigrp_master_hash_count(&eigrp_om->eigrp)) {
		eigrp = eigrp_master_hash_first(&eigrp_om->eigrp);
		eigrp_finish(eigrp);
	}

	eigrp_master_hash_fini(&eigrp_om->eigrp);

	eigrp_zebra_stop();

	vrf_terminate();
	frr_fini();
}

void eigrp_finish(struct eigrp *eigrp)
{
	eigrp_finish_final(eigrp);

	return;
}

/* Final cleanup of eigrp instance */
void eigrp_finish_final(struct eigrp *eigrp)
{
	struct eigrp_interface *ei;
	struct eigrp_neighbor *nbr;

	while (eigrp_interface_hash_count(&eigrp->eifs)) {
		ei = eigrp_interface_hash_first(&eigrp->eifs);
		while (eigrp_nbr_hash_count(&ei->nbr_hash_head)) {
			nbr = eigrp_nbr_hash_first(&ei->nbr_hash_head);
			eigrp_nbr_delete(nbr);
		}
		eigrp_if_delete_hook(ei->ifp);
	}

	EVENT_OFF(eigrp->t_write);
	EVENT_OFF(eigrp->t_read);
	close(eigrp->fd);

	eigrp_interface_hash_fini(&eigrp->eifs);
	list_delete(&eigrp->oi_write_q);

	eigrp_topology_free(eigrp, eigrp->topology_table);
	eigrp_network_free(eigrp, eigrp->networks);

	eigrp_nbr_delete(eigrp->neighbor_self);

	list_delete(&eigrp->topology_changes_externalIPV4);
	list_delete(&eigrp->topology_changes_internalIPV4);

	eigrp_master_hash_del(&eigrp_om->eigrp, eigrp);

	stream_free(eigrp->ibuf);
	distribute_list_delete(&eigrp->distribute_ctx);

	QOBJ_UNREG(eigrp);

	XFREE(MTYPE_EIGRP_TOP, eigrp);
}

/*Look for existing eigrp process*/
struct eigrp *eigrp_lookup(vrf_id_t vrf_id)
{
	struct eigrp *eigrp, lookup;

	lookup.vrf_id = vrf_id;
	eigrp = eigrp_master_hash_find(&eigrp_om->eigrp, &lookup);

	return eigrp;
}

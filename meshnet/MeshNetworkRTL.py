#=========================================================================
# MeshNetworkRTL.py
#=========================================================================
# Mesh network implementation.
#
# Author : Cheng Tan
#   Date : Mar 10, 2019

from pymtl                            import *
from network.Network                  import Network
from pclib.ifcs.SendRecvIfc           import *
from Direction                        import *
from channel.ChannelRTL               import ChannelRTL
from meshnet.meshrouter.MeshRouterRTL import MeshRouterRTL

class MeshNetworkRTL( Network ):
  def construct( s, PacketType, PositionType, mesh_wid=4, mesh_ht=4, chl_lat=0 ):

    # Constants

    s.num_routers = mesh_wid * mesh_ht
    num_channels  = (mesh_ht*(mesh_wid-1)+mesh_wid*(mesh_ht-1)) * 2

    super( MeshNetworkRTL, s ).construct( PacketType, PositionType, 
      MeshRouterRTL, ChannelRTL, SendIfcRTL, RecvIfcRTL, s.num_routers, 
      s.num_routers, num_channels, chl_lat )

    # Connect s.routers together in Mesh

    chl_id  = 0
    for i in range( s.num_routers ):
      if i / mesh_wid > 0:
        s.connect( s.routers[i].send[NORTH], s.channels[chl_id].recv )
        s.connect( s.channels[chl_id].send, s.routers[i-mesh_wid].recv[SOUTH] )
        chl_id += 1

      if i / mesh_wid < mesh_ht - 1:
        s.connect( s.routers[i].send[SOUTH], s.channels[chl_id].recv )
        s.connect( s.channels[chl_id].send, s.routers[i+mesh_wid].recv[NORTH] )
        chl_id += 1

      if i % mesh_wid > 0:
        s.connect( s.routers[i].send[WEST], s.channels[chl_id].recv )
        s.connect( s.channels[chl_id].send, s.routers[i-1].recv[EAST] )
        chl_id += 1

      if i % mesh_wid < mesh_wid - 1:
        s.connect( s.routers[i].send[EAST], s.channels[chl_id].recv )
        s.connect( s.channels[chl_id].send, s.routers[i+1].recv[WEST] )
        chl_id += 1

      # Connect the self port (with Network Interface)

      s.connect(s.recv[i], s.routers[i].recv[SELF])
      s.connect(s.send[i], s.routers[i].send[SELF])

      # Connect the unused ports

      if i / mesh_wid == 0:
        s.connect( s.routers[i].send[NORTH].rdy,         0 )
        s.connect( s.routers[i].recv[NORTH].en,          0 )
        s.connect( s.routers[i].recv[NORTH].msg.payload, 0 )

      if i / mesh_wid == mesh_ht - 1:
        s.connect( s.routers[i].send[SOUTH].rdy,         0 )
        s.connect( s.routers[i].recv[SOUTH].en,          0 )
        s.connect( s.routers[i].recv[SOUTH].msg.payload, 0 )

      if i % mesh_wid == 0:
        s.connect( s.routers[i].send[WEST].rdy,          0 )
        s.connect( s.routers[i].recv[WEST].en,           0 )
        s.connect( s.routers[i].recv[WEST].msg.payload,  0 )

      if i % mesh_wid == mesh_wid - 1:
        s.connect( s.routers[i].send[EAST].rdy,          0 )
        s.connect( s.routers[i].recv[EAST].en,           0 )
        s.connect( s.routers[i].recv[EAST].msg.payload,  0 )

    # FIXME: unable to connect a struct to a port.
    @s.update
    def up_pos():
      for y in range( mesh_ht ):
        for x in range( mesh_wid ):
          idx = y * mesh_wid + x
          s.routers[idx].pos = PositionType( x, y )
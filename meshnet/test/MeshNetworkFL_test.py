#=========================================================================
# MeshNetworkFL_test.py
#=========================================================================
# Test for NetworkRTL
#
# Author : Cheng Tan
#   Date : May 19, 2019

import tempfile
from pymtl                        import *
from ocn_pclib.rtl.queues         import NormalQueueRTL
from pclib.rtl.enrdy_queues       import *
from pclib.test.test_srcs         import TestSrcRTL
from pclib.test.test_sinks        import TestSinkRTL
from pclib.test                   import TestVectorSimulator
from ocn_pclib.ifcs.Packet        import Packet, mk_pkt
from ocn_pclib.ifcs.Position      import *
from meshnet.MeshNetworkFL        import MeshNetworkFL
# from ocn_pclib.draw               import *

#-------------------------------------------------------------------------
# Test Vector
#-------------------------------------------------------------------------
def run_vector_test( model, test_vectors, mesh_wid, mesh_ht ):
 
  def tv_in( model, test_vector ):
    num_routers = mesh_wid * mesh_ht

    for i in range( num_routers ):
      model.recv[i].rdy = 0
      model.recv[i].msg = None

    if test_vector[0] != 'x':
      router_id = test_vector[0]
      pkt = mk_pkt( router_id % mesh_wid, router_id / mesh_wid,
                  test_vector[1][0], test_vector[1][1], 1, test_vector[1][2])
    
      model.recv[router_id].rdy = 1
      model.recv[router_id].msg = pkt

  def tv_out( model, test_vector ):
    if test_vector[2] != 'x':
#      print 'index: ', test_vector[2], '; payload: ', model.send[test_vector[2]].msg, '; test_vector:', test_vector[3]
      assert model.send[test_vector[2]].msg.payload == test_vector[3]
     
  sim = TestVectorSimulator( model, test_vectors, tv_in, tv_out )
  sim.run_test()

def test_vector_mesh2x2( dump_vcd, test_verilog ):

  mesh_wid = 2
  mesh_ht  = 2
  MeshPos = mk_mesh_pos( mesh_wid, mesh_ht )
  model = MeshNetworkFL( Packet, mesh_wid, mesh_ht )

  num_routers = mesh_wid * mesh_ht 
  num_inports = 5

  x = 'x'

  # Specific for wire connection (link delay = 0) in 2x2 Mesh topology
  simple_2_2_test = [
#  router   [packet]   arr_router  msg 
  [  0,    [1,0,1001],     1,     1001 ],
  [  0,    [1,1,1002],     3,     1002 ],
  [  0,    [0,1,1003],     2,     1003 ],
  [  0,    [0,1,1004],     2,     1004 ],
  [  0,    [1,0,1005],     1,     1005 ],
  [  2,    [0,0,1006],     0,     1006 ],
  [  1,    [0,1,1007],     2,     1007 ],
  [  2,    [1,1,1008],     3,     1008 ],
  [  x,    [0,0,0000],     x,       x  ],
  ]

  # dt = DrawGraph()
  # model.set_draw_graph( dt )
  run_vector_test( model, simple_2_2_test, mesh_wid, mesh_ht)

def ttest_vector_mesh4x4( dump_vcd, test_verilog ):

  mesh_wid = 4
  mesh_ht  = 4
  MeshPos = mk_mesh_pos( mesh_wid, mesh_ht )
  model = MeshNetworkFL( Packet, MeshPos, mesh_wid, mesh_ht )

  num_routers = mesh_wid * mesh_ht 
  num_inports = 5
  for r in range (num_routers):
    for i in range (num_inports):
      path_qt = "top.routers[" + str(r) + "].input_units[" + str(i) + "].elaborate.QueueType"
      path_ru = "top.routers[" + str(r) + "].elaborate.RouteUnitType"
      model.set_parameter(path_qt, NormalQueueRTL)
      model.set_parameter(path_ru, DORYMeshRouteUnitRTL)

  x = 'x'
  # Specific for wire connection (link delay = 0) in 4x4 Mesh topology
  simple_4_4_test = [
#  router   [packet]   arr_router  msg 
  [  0,    [1,0,1001],     x,       x  ],
  [  0,    [1,1,1002],     x,       x  ],
  [  0,    [0,1,1003],     1,     1001 ],
  [  0,    [0,1,1004],     x,       x  ],
  [  0,    [1,0,1005],     4,     1003 ],
  ]

  # dt = DrawGraph()
  # model.set_draw_graph( dt )
  run_vector_test( model, simple_4_4_test, mesh_wid, mesh_ht)

  # dt.draw_topology( model.routers, model.channels )

#-------------------------------------------------------------------------
# TestHarness
#-------------------------------------------------------------------------

class TestHarness( Component ):

  def construct( s, MsgType, mesh_wid, mesh_ht, src_msgs, sink_msgs, 
                 src_initial, src_interval, sink_initial, sink_interval,
                 arrival_time=None ):

    MeshPos = mk_mesh_pos( mesh_wid, mesh_ht )
    s.dut = MeshNetworkFL( MsgType, MeshPos, mesh_wid, mesh_ht )

    s.srcs  = [ TestSrcRTL   ( MsgType, src_msgs[i],  src_initial,  src_interval  )
              for i in range ( s.dut.num_routers ) ]
    if arrival_time != None:
      s.sinks = [ TestSinkRTL  ( MsgType, sink_msgs[i], sink_initial,
                sink_interval, arrival_time[i]) for i in range ( s.dut.num_routers ) ]
    else:
      s.sinks = [ TestSinkRTL  ( MsgType, sink_msgs[i], sink_initial,
                sink_interval) for i in range ( s.dut.num_routers ) ]

    # Connections
    for i in range ( s.dut.num_routers ):
      s.connect( s.srcs[i].send, s.dut.recv[i]   )
      s.connect( s.dut.send[i],  s.sinks[i].recv )

  def done( s ):
    srcs_done = 1
    sinks_done = 1
    for i in range( s.dut.num_routers ):
      if s.srcs[i].done() == 0:
        srcs_done = 0
    for i in range( s.dut.num_routers ):
      if s.sinks[i].done() == 0:
        sinks_done = 0
    return srcs_done and sinks_done
  def line_trace( s ):
    return s.dut.line_trace()

#-------------------------------------------------------------------------
# run_rtl_sim
#-------------------------------------------------------------------------

def run_sim( test_harness, max_cycles=100 ):

  # Create a simulator

  test_harness.apply( SimpleSim )
  test_harness.sim_reset()

  # Run simulation

  ncycles = 0
  print ""
  print "{}:{}".format( ncycles, test_harness.line_trace() )
  while not test_harness.done() and ncycles < max_cycles:
    test_harness.tick()
    ncycles += 1
    print "{}:{}".format( ncycles, test_harness.line_trace() )

  # Check timeout

  assert ncycles < max_cycles

  test_harness.tick()
  test_harness.tick()
  test_harness.tick()

#-------------------------------------------------------------------------
# Test cases (specific for 4x4 mesh)
#-------------------------------------------------------------------------

def ttest_srcsink_mesh4x4_():

  #           src, dst, payload
  test_msgs = [ (0, 15, 101), (1, 14, 102), (2, 13, 103), (3, 12, 104),
                (4, 11, 105), (5, 10, 106), (6,  9, 107), (7,  8, 108),
                (8,  7, 109), (9,  6, 110), (10, 5, 111), (11, 4, 112),
                (12, 3, 113), (13, 2, 114), (14, 1, 115), (15, 0, 116) ]
  
  src_packets  =  [ [],[],[],[],
                    [],[],[],[],
                    [],[],[],[],
                    [],[],[],[] ]
  
  sink_packets =  [ [],[],[],[],
                    [],[],[],[],
                    [],[],[],[],
                    [],[],[],[] ]
  
  # note that need to yield one/two cycle for reset
  arrival_pipes = [[8], [6], [6], [8],
                   [6], [4], [4], [6], 
                   [6], [4], [4], [6], 
                   [8], [6], [6], [8]]

  mesh_wid = 4
  mesh_ht  = 4
  for (src, dst, payload) in test_msgs:
    pkt = mk_pkt( src%mesh_wid, src/mesh_wid, dst%mesh_wid, dst/mesh_wid, 1, payload )
    src_packets [src].append( pkt )
    sink_packets[dst].append( pkt )

  th = TestHarness( Packet, mesh_wid, mesh_ht, src_packets, sink_packets, 
                    0, 0, 0, 0, arrival_pipes )
  run_sim( th )

def ttest_srcsink_mesh2x2():

  pkt = mk_pkt( 0, 0, 1, 1, 0, 0xfaceb00c )

  src_packets  = [ [ pkt ], [], [], [] ]
  sink_packets = [ [], [], [], [ pkt ] ]

  th = TestHarness( Packet, 2, 2, src_packets, sink_packets, 0, 0, 0, 0 )
  run_sim( th )
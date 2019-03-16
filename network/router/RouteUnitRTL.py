#=========================================================================
# RouteUnitRTL.py
#=========================================================================
# A route unit with configurable routing strategies.
#
# Author : Cheng Tan, Yanghui Ou
#   Date : Mar 3, 2019

from pymtl import *
from pclib.ifcs.EnRdyIfc import InEnRdyIfc, OutEnRdyIfc

from ocn_pclib.Packet    import Packet
from ocn_pclib.Position  import *

class RouteUnitRTL( RTLComponent ):
  def construct( s, routing_logic, PositionType, num_outports=5 ):

    # Constants 
    s.num_outports = num_outports

    # Interface
    s.recv  = InEnRdyIfc( Packet )
    s.send  = [ OutEnRdyIfc (Packet) for _ in range ( s.num_outports ) ]
    s.pos   = InVPort( PositionType )

    # Componets
    s.routing_logic = routing_logic
    s.out_rdys = Wire( mk_bits( s.num_outports ) )
    s.out_dir  = OutVPort( Bits3  ) 

    # Connections
    for i in range( s.num_outports ):
      s.connect( s.recv.msg,    s.send[i].msg )
      s.connect( s.out_rdys[i], s.send[i].rdy )
    
    s.connect( s.pos,      s.routing_logic.pos     )  
    s.connect( s.recv.msg, s.routing_logic.pkt_in  )
    s.connect( s.out_dir,  s.routing_logic.out_dir )

    # Routing logic
    @s.update
    def up_ru_recv_rdy():
      s.recv.rdy =  s.send[s.out_dir].rdy

    @s.update
    def up_ru_send_en():
      for i in range( s.num_outports ):
        s.send[i].en = 0
      s.send[s.out_dir].en = s.recv.en and s.send[s.out_dir].rdy 

  def line_trace( s ):
    out_str = [ "" for _ in range( s.num_outports ) ]
    for i in range (s.num_outports):
      out_str[i] = "<{}>".format( s.send[i].en ) 

    return "({},{})->({},{}); dir:({}); ({}|{}|{}|{}|{}); recv.rdy({}); send.rdy({})".format(s.recv.msg.src_x, s.recv.msg.src_y, s.recv.msg.dst_x, s.recv.msg.dst_y, s.out_dir, out_str[0], out_str[1], out_str[2], out_str[3], out_str[4], s.recv.rdy, s.send[s.out_dir].rdy )

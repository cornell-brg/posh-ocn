#=========================================================================
# InputUnitRTL.py
#=========================================================================
# An input unit for the router that supports single-phit packet.
# Note that the interface is send/recv-based.
# Enabling parameter passing.
#
# Author : Yanghui Ou, Cheng Tan
#   Date : Feb 23, 2019

from pymtl import *
#from pclib.ifcs.EnRdyIfc  import InEnRdyIfc, OutEnRdyIfc
from pclib.ifcs.SendRecvIfc import *
from pclib.rtl  import NormalQueueRTL

class InputUnitRTL( RTLComponent ):
  def construct( s, PacketType, QueueType=None, num_entries=1 ):

    # Constant
    s.QueueType = QueueType

    # Interface
    s.recv = RecvIfcRTL( PacketType )
    s.send = SendIfcRTL( PacketType )

    if s.QueueType != None:
      # Component
      s.queue = s.QueueType(num_entries, Type=PacketType)
      
      # Connections
      s.connect( s.recv.rdy, s.queue.enq.rdy )
      s.connect( s.recv.en,  s.queue.enq.val )
      s.connect( s.recv.msg, s.queue.enq.msg )

      s.connect( s.send.msg, s.queue.deq.msg )
  
      @s.update
      def enSend():
        s.send.en   = s.send.rdy and s.queue.deq.val
        s.queue.deq.rdy = s.send.rdy

    else:
      s.connect( s.recv, s.send )
  
  def line_trace( s ):
    if s.QueueType != None:
      return "{}({}){}".format( s.recv.msg, s.queue.ctrl.num_entries, 
            s.send.msg )
    else:
      return "{}(0){}".format( s.recv.msg, s.send.msg)
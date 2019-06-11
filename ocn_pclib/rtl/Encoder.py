#=========================================================================
# Encoder.py
#=========================================================================
# A priority encoder for arbitration
#
# Author : Yanghui Ou, Cheng Tan
#   Date : Mar 1, 2019

from pymtl3 import *

class Encoder( Component ):
  def construct( s, in_width, out_width ):

    # Interface
    s.in_ =  InPort( mk_bits( in_width  ) )
    s.out = OutPort( mk_bits( out_width ) )
    
    # Constants
    s.din_wid  = in_width
    s.dout_wid = out_width

    # Logic
    @s.update
    def encode():
      #TODO: need to change the bitwidth for correct translation.
      s.out = Bits3(0)
      for i in range( in_width ):
        s.out = Bits3(i) if s.in_[i] else s.out
  
  def line_trace( s ):
    return "in:{:0>{n}b} | out:{}".format( int( s.in_ ), s.out, n=s.din_wid ) 

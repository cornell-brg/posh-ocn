#!/usr/bin/env python
"""
=========================================================================
pyocn.py
=========================================================================
Example of PyOCN for modeling, testing, and evaluating.

Author : Cheng Tan
  Date : July 30, 2019
"""
import os
import sys
import argparse
import re

from collections import deque
from random      import seed, randint

sim_dir = os.path.dirname( os.path.abspath( __file__ ) )
os.system(sim_dir)
while sim_dir:
  if os.path.exists( sim_dir + os.path.sep + ".pymtl-python-path" ):
    sys.path.insert(0,sim_dir)
    # include the pymtl environment here
    # sys.path.insert(0,sim_dir + "/../pymtl3/")
    break
  sim_dir = os.path.dirname(sim_dir)
  os.system(sim_dir)

#from meshnet.MeshNetworkFL    import MeshNetworkFL
#from crossbar.CrossbarRTL     import CrossbarRTL
from pymtl3                   import *
from meshnet.MeshNetworkCL    import MeshNetworkCL
from ringnet.RingNetworkRTL   import RingNetworkRTL
from meshnet.MeshNetworkRTL   import MeshNetworkRTL
from cmeshnet.CMeshNetworkRTL import CMeshNetworkRTL
from torusnet.TorusNetworkRTL import TorusNetworkRTL
from bflynet.BflyNetworkRTL   import BflyNetworkRTL
from ocn_pclib.ifcs.packets   import *
from ocn_pclib.ifcs.positions import *
from pymtl3.stdlib.test       import TestVectorSimulator
from pymtl3.passes.sverilog   import ImportPass, TranslationPass
from ocn_pclib.passes.PassGroups import SimulationPass

import time

seed(0xdeadbeef)

#-------------------------------------------------------------------------
# Command line processing
#-------------------------------------------------------------------------

#--------------------------------------------------------------------------
# generate
#--------------------------------------------------------------------------

def generate( model, topology, nodes, rows, channel_lat, packets ):
  perform( 'generate', model, topology, nodes, rows, channel_lat, 0,
           None, packets )

#--------------------------------------------------------------------------
# characterize
#--------------------------------------------------------------------------

def characterize():
  pass

#--------------------------------------------------------------------------
# simulate
#--------------------------------------------------------------------------

def simulate( model, topology, nodes, rows, channel_lat, injection, pattern ):
  return perform( 'simulate', model, topology, nodes, rows, channel_lat, injection,
                  pattern, None )

# Global constants for simulation

NUM_WARMUP_CYCLES   = 10
NUM_SAMPLE_CYCLES   = 50 + NUM_WARMUP_CYCLES
INVALID_TIMESTAMP   = 0

def perform( action, model, topology, nodes, rows, channel_lat, injection,
             pattern, packets ):

  routers         = nodes
  channel_latency = channel_lat
  injection_rate  = injection * 100
  net             = None

  # Simulation Variables

  average_latency       = 0.0
  packets_generated     = 0
  packets_received      = 0
  all_packets_received  = 0
  total_latency         = 0
  drain_cycles          = 0
  sim_done              = False

  # Determine which model to use in the simulator

  if model == "CL":
    if topology == "ring":
      NetModel = RingNetworkCL
    elif topology == "mesh":
      NetModel = MeshNetworkCL
    elif topology == "cmesh":
      NetModel = CMeshNetworkCL
    elif topology == "torus":
      NetModel = TorusNetworkCL
    elif topology == "bfly":
      NetModel = BflyNetworkCL

  elif model == "RTL":
    # Instantiate and elaborate a ring network

    if topology  == "Ring":
      NetModel   = RingNetworkRTL
      RingPos    = mk_ring_pos( routers )
      PacketType = mk_ring_pkt_timestamp( routers, payload_nbits = 32,
                   nvcs = 2, max_time = NUM_SAMPLE_CYCLES )
      net        = NetModel( PacketType, RingPos, routers, channel_lat )
#      net.set_param( "top.routers*.route_units*.construct", num_routers=routers)

    elif topology == "Mesh":
      NetModel    = MeshNetworkRTL
      net_width   = routers // rows
      net_height  = rows
      MeshPos     = mk_mesh_pos( net_width, net_height )
      PacketType  = mk_mesh_pkt_timestamp( net_width, net_height,
                    payload_nbits = 32, max_time = NUM_SAMPLE_CYCLES )
      net         = NetModel( PacketType, MeshPos,
                    net_width, net_height, channel_lat )

    elif topology == "Torus":
      NetModel    = TorusNetworkRTL
      net_width   = routers // rows
      net_height  = rows
      MeshPos     = mk_mesh_pos( net_width, net_height )
      PacketType  = mk_mesh_pkt_timestamp( net_width, net_height,
                    payload_nbits = 32, nvcs = 2,
                    max_time = NUM_SAMPLE_CYCLES )
      net         = NetModel( PacketType, MeshPos, net_width, net_height, 0 )
      # model.set_param('top.routers*.route_units*.construct', ncols=net_width )
      # model.set_param('top.routers*.route_units*.construct', nrows=net_height)

    elif topology == "CMesh":
      # TODO: need to provide parameters for different topology specifically.
      NetModel    = CMeshNetworkRTL
      routers     = rows * rows
      net_width   = routers // rows
      net_height  = rows
      term_each   = nodes // routers
      inports     = term_each + 4
      outports    = term_each + 4
      MeshPos     = mk_mesh_pos( net_width, net_height )
      PacketType  = mk_cmesh_pkt_timestamp( net_width, net_height,
                    inports, outports, payload_nbits = 32,
                    max_time = NUM_SAMPLE_CYCLES )
      net         = NetModel( PacketType, MeshPos, net_width, net_height,
                    term_each, 0 )

    elif topology == "Bfly":
      NetModel    = BflyNetworkRTL
      k_ary       = 4
      n_fly       = 3
      nodes   = k_ary * ( k_ary ** ( n_fly - 1 ) )
      num_routers = n_fly * ( k_ary ** ( n_fly - 1 ) )
      MeshPos     = mk_bfly_pos( k_ary, n_fly )
      PacketType  = mk_bfly_pkt_timestamp( k_ary, n_fly,
                    payload_nbits = 32, max_time = NUM_SAMPLE_CYCLES )
      net         = NetModel( PacketType, MeshPos, k_ary, n_fly, 0 )
      net.set_param( "top.routers*.construct", k_ary=k_ary )
      net.set_param( "top.routers*.route_units*.construct", n_fly=n_fly )

  net.elaborate()
  if action == "generate":
    net.sverilog_translate = True
    net.dump_vcd = True
    net.vcd_file_name = "dumpVCD"
    net.apply( TranslationPass() )
  sim = net.apply( SimulationPass )

  # Source Queues - Modeled as Bypass Queues
  src_queue = [ deque() for x in range( nodes ) ]

  # Run the simulation

  net.sim_reset()
  for i in range( nodes ):
    net.send[i].rdy = Bits1(1)

    if topology == "Mesh":
      XYType = mk_bits( clog2( net_width ) )
      net.pos_x[i] = XYType(i % net_width)
      net.pos_y[i] = XYType(i // net_height)

  ncycles = 0

  while not sim_done:
    # Iterate over all terminals
    for i in range( nodes ):

      # Generate packet

      if ( (action == "simulate" and randint( 1, 100 ) <= injection_rate) or
           (action == "generate" and packets[0]['src'] == i) ):

        if (action == "simulate"):
          # traffic pattern based dest selection
          if   pattern == "urandom":
            dest = randint( 0, nodes-1 )
          elif pattern == "partition":
            dest = ( randint( 0, nodes-1 ) ) & (nodes // 2-1) |\
                   ( i & (nodes // 2) )
          elif pattern == "opposite":
            dest = ( i + 2 ) % nodes
          elif pattern == "neighbor":
            dest = ( i + 1 ) % nodes
          elif pattern == "complement":
            dest = i ^ (nodes-1)
          src = i
          data = Bits32(6)
  
        if (action == "generate"):
          src  = packets[0]['src']
          dest = packets[0]['dest']
          data = Bits32(packets[0]['data'])
          packets.popleft()

        # inject packet past the warmup period
  
        timestamp = INVALID_TIMESTAMP
        if ( NUM_WARMUP_CYCLES < ncycles < NUM_SAMPLE_CYCLES ):
          timestamp = ncycles
  
        if topology == "Ring":
          pkt = PacketType( src, dest, 0, 0, data, timestamp )
  
        elif topology == "Mesh":
          XYType = mk_bits( clog2( net_width ) )
          timeType = mk_bits(clog2(NUM_SAMPLE_CYCLES+1))
          pkt = PacketType( XYType(src%net_width), XYType(src//net_width), 
                  XYType(dest % net_width), XYType(dest//net_width), 
                  Bits8(0), data, timeType(timestamp) )
  
  
        elif topology == "Torus":
          pkt = PacketType( src % net_width, src // net_width, dest % net_width,
                  dest // net_width, 0, 0, data, timestamp )
  
        elif topology == "CMesh":
          pkt = PacketType( (src // term_each) %  net_width,
                            (src // term_each) // net_width,
                            (dest // term_each) %  net_width,
                            (dest // term_each) // net_width,
                            dest % term_each,
                            0, data, timestamp )
  
        elif topology == "Bfly":
          r_rows = k_ary ** ( n_fly - 1 )
          if r_rows == 1 or k_ary == 1:
            DstType = mk_bits( n_fly )
          else:
            DstType = mk_bits( clog2( k_ary ) * n_fly )
          bf_dst = DstType(0)
          tmp = 0
          dst = dest
          for index in range( n_fly ):
            tmp = dst // (k_ary**(n_fly-index-1))
            dst = dst %  (k_ary**(n_fly-index-1))
            bf_dst = DstType(bf_dst | DstType(tmp))
            if index != n_fly - 1:
              if k_ary == 1:
                bf_dst = bf_dst * 2
              else:
                bf_dst = bf_dst * k_ary
          pkt = PacketType( src, bf_dst, 0, data, timestamp )
  
        src_queue[src].append( pkt )
        if ( ncycles < NUM_SAMPLE_CYCLES ):
          packets_generated += 1

        # Inject from source queue

      if ( len( src_queue[i] ) > 0 ):
        if net.recv[i].rdy:
          net.recv[i].msg = src_queue[i][0]
          net.recv[i].en  = Bits1(1)
        else:
          net.recv[i].en  = Bits1(0)
      else:
        net.recv[i].en  = Bits1(0)

      # Receive a packet

      if ( net.send[i].en == 1 ):
        timestamp = net.send[i].msg.timestamp
        all_packets_received += 1

        # collect data for measurement packets
        if ( timestamp != INVALID_TIMESTAMP ):
          total_latency    += ( ncycles - timestamp )
          packets_received += 1
          average_latency = int( total_latency ) / float( packets_received )

      # Check if finished - drain phase

      if action == 'simulate':
        if ( ncycles >= NUM_SAMPLE_CYCLES and
             all_packets_received >= packets_generated ):
          average_latency = int( total_latency ) / float( packets_received )
          sim_done = True
          break
      elif action == 'generate':
        if ( all_packets_received >= packets_generated ):
          sim_done = True
          break

      # Pop the source queue

      if ( net.recv[i].rdy == Bits1(1) ) and ( len( src_queue[i] ) > 0 ):
        src_queue[i].popleft()

    # print line trace if enables

#    print( "{:3}:{}".format( ncycles, net.line_trace() ))

    net.tick()
    ncycles += 1

  # return the calculated average_latency and count of packets received

  return [average_latency, packets_received, ncycles]

#-------------------------------------------------------------------------
# Main
#-------------------------------------------------------------------------

from ruamel.yaml import YAML
from pathlib import Path

def main():

  path   = Path('config.yml')
  yaml   = YAML(typ='safe')
  config = yaml.load(path)

  print( config )
  print( config['topology'] )

  for action in config['action']:

    if action == 'generate':
      print()
      print( "[GENERATE]" )
      print( "=======================================================================================" )
      packets = config['packets']
      for model in config['model']:
        for topology in config['topology']:
          results = generate( model, topology, config['nodes'], config['rows'],
                    config['channel_lat'], packets )

    if action == 'simulate':

      print()
      print( "[SIMULATE]" )
      print( "Warmup Cycles:    %d" % NUM_WARMUP_CYCLES )
      print( "Sample Cycles:    %d" % NUM_SAMPLE_CYCLES )
      print( "=======================================================================================" )
      print( "|Model|Topology|Pattern    |Inj.Rate|Avg.Lat|Num.Pkt|Total Cycles|Sim.Time|Speed (c/s)|" )
      print( "|-----|--------|-----------|--------|-------|-------|------------|--------|-----------|" )

      for model in config['model']:
        for topology in config['topology']:
          for injection in config['injection']:
            for pattern in config['pattern']:
              start_time = time.time()

              # Start simulation

              results = simulate( model, topology, config['nodes'], config['rows'],
                        config['channel_lat'], injection, pattern )

              end_time = time.time()

              print( "|{:<5}|{:<8}|{:<11}|{:<8}|{:<7}|{:<7}|{:<12}|{:<8}|{:<11}|".\
                      format(model, topology, pattern, injection,\
                          "{0:.1f}".format(results[0]), results[1], results[2],
                          "{0:.1f}".format(end_time - start_time),
                          "{0:.1f}".format(results[2]/(end_time - start_time))) )

      print( "|=====================================================================================|" )
      print()

main()


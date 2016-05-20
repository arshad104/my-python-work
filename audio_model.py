import numpy as np
from random import shuffle
from IPython import embed
import nn_functions as nn_func

from neural_nodes import *
import cProfile, pstats, io
import matplotlib.pyplot as plt
from graph import *
import pymongo
from audio_server_2 import AudioServer2
from wordvec_server import WordvecServer
from pymongo import MongoClient
from pymongo import ReturnDocument
from pycallgraph import PyCallGraph
from pycallgraph.output import GraphvizOutput
from influx_client import InfluxClient
from word_weight_mapper import WordWeightMapper
import gc
import random
import json
import ctc as ctc

os.environ['CUDARRAY_BACKEND'] = 'numpy'
import cudarray as ca


class TrainingSession:
  def __init__(self,kwargs):
    self.iterations = self.arg_exists(kwargs,'iterations')
    self.log_error = self.arg_exists(kwargs,'log_error')
    self.log_grad = self.arg_exists(kwargs,'log_grad')
    self.log_activation = self.arg_exists(kwargs,'log_activation')
    self.batch_size = 1
    self.master_graph = MasterGraph({'batch_size':self.batch_size,'log_grad':self.log_grad,'log_activation':self.log_activation,'log_error':self.log_error})
    self.iteration_number = 0
    self.weight_persist_freq = self.arg_exists(kwargs,'weight_persist_freq')
    self.error_history = []
    self.classification_history = []
    self.client = MongoClient("mongodb://root:rOotAdmin76@market1.awok:27017")
    self.db = self.client.mind
    self.collection = self.db.network_topology                                          

  def train(self):
    self.master_graph.observation_server = AudioServer2({})
    self.master_graph.dt = WordvecServer({})
    self.master_graph.word_weight_mapper = WordWeightMapper()

    
    mold = {'name':'conv_origin','type': 'conv_origin','size':100}
    Graph({'name':'conv_origin','type':'conv_origin','master_graph':self.master_graph,'batch_size':1}).build_graph({'batch_size':self.batch_size,'master_graph':self.master_graph,'name':mold['name'],'mold':mold})

    mold = {'name':'row_conv_origin','type': 'row_conv_origin','size':100}
    Graph({'name':'row_conv_origin','type':'row_conv_origin','master_graph':self.master_graph,'batch_size':1}).build_graph({'batch_size':self.batch_size,'master_graph':self.master_graph,'name':mold['name'],'mold':mold})

    mold = {'name':'row_conv_classifier_origin','type': 'row_conv_classifier_origin','size':100}
    Graph({'name':'row_conv_classifier_origin','type':'row_conv_classifier_origin','master_graph':self.master_graph,'batch_size':1}).build_graph({'batch_size':self.batch_size,'master_graph':self.master_graph,'name':mold['name'],'mold':mold})

    i = 0
    #request an observation from AudioServer, AudioServer makes the observation available with a reference
    _iter = self.master_graph.observation_server.__iter__()
    while i < self.iterations:
      self.master_graph.predicted_words =[]
      self.master_graph.reset_except_origin()
      observation = _iter.next()
      self.master_graph.word_weight_mapper.words(observation['tokens'])
      wave_length = observation['audio'].size / 1024
      print "wave_length - " + str(wave_length)

      x = [observation['k'],'audio']
      
      mold = {'name':'conv','type': 'conv', 'key':x,'size':100,'img_shape':(observation['audio'].shape[2],observation['audio'].shape[3])}
      Graph({'name':'conv','type':'conv','master_graph':self.master_graph,'batch_size':1}).build_graph({'batch_size':self.batch_size,'master_graph':self.master_graph,'name':mold['name'],'mold':mold})

      mold = {'type':None}
      Graph({'name':'slicer_g','type':'slicer','master_graph':self.master_graph,'batch_size':1}).build_graph({'mold':mold})
      
      # slicer layer
      for j in xrange(wave_length):
        self.master_graph.graph['slicer_g'].add_node({'class':'SlicerNode','name':'slicer-' + str(j),'opts':{'start_slice':(j * 128),'end_slice':((j+1) * 128)}})
        self.master_graph.graph['slicer_g'].add_children({'parent':'slicer-' + str(j),'children':[['conv','n24.1.c']]})
      
      # first row conv
      for j in xrange(wave_length):
        if j == (wave_length-1):
          last_graph = True
        else:
          last_graph = False

        mold = {'name':'row_conv_1_' + str(j),'type': 'row_conv','graph_index':j,'graph_level':0,'bottom_graph':'slicer_g','last_graph':last_graph}
        Graph({'name':'row_conv_1_' + str(j),'type':'row_conv','master_graph':self.master_graph,'batch_size':1}).build_graph({'batch_size':self.batch_size,'master_graph':self.master_graph,'name':mold['name'],'mold':mold})
      
      # second row conv
      for j in xrange(wave_length):
        if j == (wave_length-1):
          last_graph = True
        else:
          last_graph = False

        mold = {'name':'row_conv_2_' + str(j),'type': 'row_conv','graph_index':j,'graph_level':1,'bottom_graph':'row_conv_1','last_graph':last_graph}
        Graph({'name':'row_conv_2_' + str(j),'type':'row_conv','master_graph':self.master_graph,'batch_size':1}).build_graph({'batch_size':self.batch_size,'master_graph':self.master_graph,'name':mold['name'],'mold':mold})    

      blanks = wave_length - len(observation['tokens'])

      k=0
      for j in xrange(wave_length):
        if j == (wave_length-1):
          last_graph = True
        else:
          last_graph = False

        loss_distribution = ctc.build_ctc_distribution( (len(observation['tokens'])+2) ,wave_length)

        print self.master_graph.word_weight_mapper.weight_mat.shape[1]
        temp_mat = np.zeros((1,self.master_graph.word_weight_mapper.weight_mat.shape[1]),dtype = np.float32)

        char_prob_dict = {}
        for t_i, token in enumerate(observation['tokens']):
          if token in char_prob_dict:
            char_prob_dict[token] += loss_distribution[j][t_i+1]
          else:
            char_prob_dict[token] = loss_distribution[j][t_i+1]
        char_prob_dict['<blank>'] = loss_distribution[j][0]     

        for k,v in char_prob_dict.iteritems():
          temp_mat[0,self.master_graph.word_weight_mapper.dict[k]] = v
        y = ca.array(temp_mat)
        
        mold = {'name':'row_conv_3_' + str(j),'type': 'row_conv_classifier','graph_index':j,'graph_level':2,'bottom_graph':'row_conv_2','y':y,'last_graph':last_graph}
        Graph({'name':'row_conv_3_' + str(j),'type':'row_conv_classifier','master_graph':self.master_graph,'batch_size':1}).build_graph({'batch_size':self.batch_size,'master_graph':self.master_graph,'name':mold['name'],'mold':mold})  
        
      
      self.master_graph.forward()

      self.master_graph.backward()  
      
      self.master_graph.update_weights()

      self.master_graph.graph['row_conv_classifier_origin'].nodes['w-classify'].activation_status = False
     
      self.master_graph.print_error(i)

      self.master_graph.reset_grads()

      i += 1
      
  def arg_exists(self,dictio,arg):
    if arg in dictio: 
      return dictio[arg]
    else:
      return None

  

t = TrainingSession({'iterations':50000000,'time_frame':2,'batch_size':1,'log_grad':False,'log_activation':False,'log_error':True})


# pr = cProfile.Profile()
# pr.enable()

t.train()

# pr.disable()
# s = io.StringIO()
# sortby = 'cumulative'
# ps = pstats.Stats(pr, stream=s).sort_stats(sortby)

# ps.dump_stats('program.prof')


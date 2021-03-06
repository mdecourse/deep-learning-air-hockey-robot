#!/usr/bin/env python

import os
os.environ['CUDA_DEVICE_ORDER'] = 'PCI_BUS_ID'
os.environ['CUDA_VISIBLE_DEVICES'] = ''

import sys
dir_path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(dir_path + '/supervised/utils')
sys.path.append(dir_path + '/supervised/keras')

import argparse
import numpy as np
from keras.models import load_model
from caffe2.python import workspace
from caffe2.python.predictor import mobile_exporter

import keras_to_caffe2
from metrics import fmeasure, recall, precision

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--data_file', default=None, help='file with test data')
    parser.add_argument('-m', '--model_file', default=None, help='file containing keras model')
    args = parser.parse_args()
    data_file = args.data_file
    model_file = args.model_file

    # Load keras model
    keras_model = load_model(model_file, {'fmeasure': fmeasure, 'recall': recall, 'precision': precision})
    
    # Copy from keras to caffe2
    caffe2_model = keras_to_caffe2.keras_to_caffe2(keras_model)
    
    # Test 
    if data_file != None: 
        n_correct = 0
        # Load Data
        from data_utils import load_data
        frames, labels = load_data(data_file)
        
        for frame in frames:
            frame = frame.reshape((1, 9, 128, 128))
            keras_pred = keras_model.predict(frame)[0]
            workspace.FeedBlob('in', frame)
            workspace.RunNet(caffe2_model.net)
            caffe2_pred = workspace.FetchBlob('out')[0]
            
            def print_array(array):
                for x in array:
                    print('%e' % (x), end =' ')
                print()
            print_array(keras_pred)
            print_array(caffe2_pred)
            
            keras_label = np.argmax(keras_pred)
            caffe2_label = np.argmax(caffe2_pred)
            match = keras_label == caffe2_label
            print('%d %s %d' % (keras_label, '==' if match else '!=', caffe2_label))
            
            n_correct += match
        print('%d correct out of %d' % (n_correct, frames.shape[0]))
    
    # Export caffe2 to Android
    init_net, predict_net = mobile_exporter.Export(workspace, caffe2_model.net, caffe2_model.params)
    with open('init_net.pb', 'wb') as f:
        f.write(init_net.SerializeToString())
    with open('predict_net.pb', 'wb') as f:
        f.write(predict_net.SerializeToString())

    print('Saved keras model as init_net.pb and predict_net.pb')
    
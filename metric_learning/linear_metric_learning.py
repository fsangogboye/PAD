'''Trains a simple deep NN on the MNIST dataset.
Gets to 98.40% test accuracy after 20 epochs
(there is *a lot* of margin for parameter tuning).
2 seconds per epoch on a K520 GPU.
'''

# from __future__ import print_function
# import theano
# theano.config.device = 'gpu'
# theano.config.floatX = 'float32'

import copy

import numpy as np
import numpy.random as rng
import pandas as pd
import keras
from keras.models import Sequential, Model
from keras.layers import Dense, Dropout, Activation, Add, Merge, Input, merge
from keras.optimizers import RMSprop, Adam
from keras.preprocessing import sequence
from keras import backend as K
from keras.layers.normalization import BatchNormalization
from keras.callbacks import ModelCheckpoint
from keras.regularizers import l2
from sklearn.preprocessing import StandardScaler
np.random.seed(0)



class Linear_Metric:

    def train(self, data_pairs, similarity_labels):
        self.scaler = StandardScaler()
        self.batch_size = 10
        self.epochs = 4
        X1 = []
        X2 = []
        for x, y in data_pairs:
            X1.append(x)
            X2.append(y)
        print(len(X1), len(X2), len(similarity_labels))
        number_classes = len(np.unique(similarity_labels)) 
        # convert class vectors to binary class matrices

        train_portion = 0.8
        input_shape = data_pairs[0][0].shape
        # kernels = int(round(input_shape[0]))
        kernels = 100
        s_size = len(similarity_labels)
        x1_train = X1[:int(s_size * train_portion)]
        x2_train = X2[:int(s_size * train_portion)]
        x1_test = X1[int(s_size * train_portion):]
        x2_test = X2[int(s_size * train_portion):]
        y_train = similarity_labels[:int(s_size * train_portion)]
        y_test = similarity_labels[int(s_size * train_portion): ]

        labels = keras.utils.to_categorical(similarity_labels, number_classes)
        y_train = keras.utils.to_categorical(y_train, number_classes)
        y_test = keras.utils.to_categorical(y_test, number_classes)

        left_input = Input(input_shape)
        right_input = Input(input_shape)
        #build f(x) to use in each siamese 'leg'
        model = Sequential()

        # model.add(Dense(kernels, input_shape = input_shape))
        # model.add(Dense(kernels))
        # model.add(Dense(kernels))

        model.add(Dense(kernels, activation='linear', input_shape = input_shape))
        model.add(Dropout(0.2))
        model.add(Dense(kernels, activation='linear'))
        model.add(Dropout(0.2))
        model.add(Dense(kernels, activation='linear'))

        # model.add(Dense(kernels,  input_shape = input_shape, kernel_regularizer=l2(2e-4)))
        # model.add(Dense(kernels,  kernel_regularizer=l2(2e-4)))
        # model.add(Dense(kernels,  kernel_regularizer=l2(1e-3)))

        #encode each of the two inputs into a vector with the model
        encoded_l = model(left_input)
        encoded_r = model(right_input)

        #merge two encoded inputs with the l1 distance between them
        L1_distance = lambda x: K.abs(x[0]-x[1])
        both = merge([encoded_l, encoded_r], mode = L1_distance, output_shape=lambda x: x[0])
        prediction = Dense(number_classes)(both)
        siamese_net = Model(input=[left_input,right_input],output=prediction)

        # optimizer = Adam(0.00006)
        optimizer = RMSprop()
        # siamese_net.compile(loss="binary_crossentropy", optimizer=optimizer)
        siamese_net.compile(loss=self.contrastive_loss, optimizer=optimizer)
    
        siamese_net.count_params()

        x1_train = np.array(x1_train)
        x2_train = np.array(x2_train)
        y_train = np.array(y_train)

        x1_test = np.array(x1_test)
        x2_test = np.array(x2_test)
        y_test = np.array(y_test)

        x1_train = np.array(X1)
        x2_train = np.array(X2)
        y_train = keras.utils.to_categorical(similarity_labels, number_classes)

        data = np.append(x1_train, x2_train, axis=0)
        
        self.scaler.fit(data)
        x1_train = self.scaler.transform(x1_train)
        x2_train = self.scaler.transform(x2_train)

        history = siamese_net.fit([x1_train, x2_train], y_train,
                            batch_size=self.batch_size,
                            epochs=self.epochs,
                            validation_data=([x1_train, x2_train], y_train), verbose=0)

        score = siamese_net.evaluate([x1_test, x2_test], y_test, verbose=0)
        print('Test loss:', score)
        print('Test accuracy:', score)
        
        inp1, inp2 = siamese_net.input

        func = siamese_net.layers[-2].input
        dist = siamese_net.layers[-2].output    
        self.functor1 = K.function([inp1]+ [K.learning_phase()], [func[0]]) 
        self.functor2 = K.function([inp2]+ [K.learning_phase()], [func[1]])
        self.functor3 = K.function([*[inp1, inp2]]+ [K.learning_phase()], [dist])

          
    def transform(self, data_pairs):
        x, y = data_pairs

        x = self.scaler.transform(np.array([x]))
        y = self.scaler.transform(np.array([y]))
        
        # x = x.reshape(1, x.shape[0])
        # y = y.reshape(1, y.shape[0])
        distance = self.functor3([*[x, y], 1.])
        return distance[0].mean()

    def contrastive_loss(self, y_true, y_pred):
        margin = 1
        return K.mean((1-y_true) * 0.5 * K.square(y_pred) + 0.5 * y_true * K.square(K.maximum(margin - y_pred, 0)))

    
    def penalized_loss(self, branch1, branch2):
        def loss(y_true, y_pred):
            return K.mean(K.square(y_pred - y_true) - K.square(y_true - y_pred), axis=-1)
        return loss

    def euclideanSqDistance(self, inputs):
        if (len(inputs) != 2):
            raise 'oops'
        output = K.mean(K.square(inputs[0] - inputs[1]), axis=-1)
        output = K.expand_dims(output, 1)
        return output

    def W_init(self, shape,name="weigt"):
        """Initialize weights as in paper"""
        values = rng.normal(loc=0,scale=1e-2,size=shape)
        return K.variable(values,name=name)
        #//TODO: figure out how to initialize layer biases in keras.

    def b_init(self, shape,name="bais"):
        """Initialize bias as in paper"""
        values = rng.normal(loc=0.5,scale=1e-2,size=shape)
        return K.variable(values,name=name)

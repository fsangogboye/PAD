import sys;
import os
import numpy as np
import time

sys.path.insert(0,os.path.abspath("./"))
from framework.framework import Framework
from framework.similarity.arrivalsimilarity import ArrivalSimilarity
from framework.similarity.segmentsimilarity import SegmentSimilarity
from framework.similarity.globalsimilarity import GlobalSimilarity
from framework.similarity.similarityterms import SimilarityTerms
from framework.utilities.datadescriptor import DataDescriptorMetadata,DataDescriptorTimeSeries,DataDescriptorTerms
from framework.metric_learning.metriclearningterms import MetricLearningTerms
import pandas as pd
import pickle
import math

inputFile = "HamiltonData_presence"
data = pd.read_csv("./dataset/Preprocssed_"+inputFile+".csv")
data = data.iloc[0:11,0:30241] # the database to be published

data = data.infer_objects()
all_data = []
all_samplingRates = []

for i in range(0,7):
    data_line_counter = pd.read_csv("./dataset/preprocessed_line_counter.csv")
    data_Noices = pd.read_csv("./dataset/Preprocessed_noices_avg_4s.csv")

    data_presence = pd.read_csv("./dataset/Preprocssed_HamiltonData_presence.csv")

    data_line_counter = data_line_counter.iloc[:,0:10081]
    data_presence = data_presence.iloc[0:11,0:30241]
    data_Noices = data_Noices.iloc[:,0:2017]

    all_data.append(data_line_counter)
    all_data.append(data_presence)
    all_data.append(data_Noices)

    all_samplingRates.append(DataDescriptorTerms.MINUET.value)
    all_samplingRates.append(DataDescriptorTerms.SECOND_20.value)
    all_samplingRates.append(DataDescriptorTerms.MINUET_5.value)

    print("amount of samples %s" % len(data.index))
    print("amount of columns %s" % len(data.columns))
    anonymity_level = 5
    rep_mode = "mean"
    min_resample_factor = math.floor(DataDescriptorTerms.DAY.value / DataDescriptorTerms.SECOND_20.value)

    k_fold = [i,7]
    framework = Framework(data,anonymity_level,rep_mode=rep_mode, resample_factor = min_resample_factor, learning_metric=MetricLearningTerms.LINEAR, k_fold= k_fold,output_groupper_after=True, all_data=all_data, all_sampling_rates= all_samplingRates)

    sampling_frequency = DataDescriptorTerms.SECOND_20
    output_generality = DataDescriptorTerms.SECOND_20
    generality_mode = DataDescriptorTerms.MEAN
    data_type = DataDescriptorTerms.BOOLEAN
    segment = [1440,2880]

    dd = DataDescriptorTimeSeries(sampling_frequency,generality_mode,data_type,1,len(data.columns)-1, output_frequency=output_generality)

    segmentedData = SegmentSimilarity(dd,segment)

    metaData = DataDescriptorMetadata(0, data_description="Meta Data")

    framework.add_similarity(segmentedData)
    framework.add_meta_data(metaData)
    start = time.clock()
    out , loss_metric, anonymity_level = framework.anonymize()
    timeOut = time.clock() - start

    pickle.dump([out, framework.generated_data_description(), loss_metric,anonymity_level,timeOut], open('./results/presence/day/PAD_results_day_'+inputFile+'_fold_'+str(i)+'.pickle', "wb"))
    print("Time: " + str(timeOut))
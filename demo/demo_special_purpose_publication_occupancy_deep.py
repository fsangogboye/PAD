import sys; import os
sys.path.append(os.path.abspath("./"))
from helper import Utilities, PerformanceEvaluation
import pandas as pd
from metric_learning import Subsampling, MetricLearning
from user_feedback import Similarity
from scipy.misc import comb
from deep import Deep_Metric

"""
In the demo, we will showcase an example of special purpose publication.
The data user wants the published database to maximally retain the information about lunch time.
"""

# Initialization of some useful classes
util = Utilities()
pe = PerformanceEvaluation()
mel = MetricLearning()


# step 1: get the database to be published
day_profile = pd.read_pickle('./dataset/dataframe_all_binary.pkl')
day_profile = day_profile.iloc[0::4,0::60]
print(day_profile)
exit()
rep_mode = 'mean'
anonymity_level = 2 # desired anonymity level

# step 2: data user specifies his/her interest. In the example, the data user is interested in preserving the
# information of a segment of entire time series. In this case, he/she would also need to specify the starting and
# ending time of the time series segment of interest.
interest = 'segment'
window = [17,21] # window specifies the starting and ending time of the period that the data user is interested in

# step 3: pre-sanitize the database
sanitized_profile_baseline = util.sanitize_data(day_profile, distance_metric='euclidean',
                                                anonymity_level=anonymity_level,rep_mode = rep_mode)

loss_generic_metric = pe.get_information_loss(data_gt=day_profile,
                                              data_sanitized=sanitized_profile_baseline.round(),
                                              window=window)

print("information loss with generic metric %s" % loss_generic_metric)
df_subsampled_from = sanitized_profile_baseline.drop_duplicates().sample(frac=1)


subsample_size_max = int(comb(len(df_subsampled_from),2))
print('total number of pairs is %s' % len(df_subsampled_from))
# print(len(day_profile))
# exit()

# step 4: sample a subset of pre-sanitized database and form the data points into pairs
subsample_size = int(round(subsample_size_max))
sp = Subsampling(data=df_subsampled_from)
data_pair = sp.uniform_sampling(subsample_size=subsample_size)

# User receives the data pairs and label the similarity
sim = Similarity(data=data_pair)
sim.extract_interested_attribute(interest=interest, window=window)
similarity_label, class_label, data_subsample = sim.label_via_silhouette_analysis(range_n_clusters=range(2,8))

# Utilize deep learning to transform data pairs for similarity learning 
input_shape = data_pair[0][0].shape
dm = Deep_Metric(input_shape, (data_subsample, class_label))
dm.train()
deep_pairs = []
for dat in data_pair:
    dat1 = dm.transform(dat[0].values)
    dat2 = dm.transform(dat[1].values)
    deep_pairs.append((dat1, dat2))


# step 5: PAD learns a distance metric that represents the interest of the user from the labeled data pairs
# lam_vec is a set of candidate lambda's for weighting the l1-norm penalty in the metric learning optimization problem.
# The lambda that achieves lowest testing error will be selected for generating the distance metric

dist_metric = mel.learn_with_simialrity_label_regularization(data=data_pair,
                                                             label=similarity_label,
                                                             lam_vec=[0, 0.1, 1, 10],
                                                             train_portion=0.8)


dist_metric_deep = mel.learn_with_simialrity_label_regularization(data=deep_pairs,
                                                             label=similarity_label,
                                                             lam_vec=[0, 0.1, 1, 10],
                                                             train_portion=0.8)
deep_day_profile = pd.DataFrame(columns=day_profile.index)
for index in day_profile.index:
    profile = day_profile.loc[index].values
    deep_day_profile[index] = dm.transform(profile)
deep_day_profile = deep_day_profile.transpose()

# day_profile = deep_day_profile 
# step 6: the original database is privatized using the learned metric

sanitized_profile = util.sanitize_data(day_profile, distance_metric="mahalanobis",
                                       anonymity_level=anonymity_level, rep_mode=rep_mode, VI=dist_metric)


sanitized_profile_deep = util.sanitize_data_deep(day_profile, deep_day_profile,  distance_metric="mahalanobis",
                                       anonymity_level=anonymity_level, rep_mode=rep_mode, VI=dist_metric_deep)

# (optionally for evaluation purpose) Evaluating the information loss of the sanitized database
loss_learned_metric = pe.get_information_loss(data_gt=day_profile,
                                              data_sanitized=sanitized_profile.round(),
                                              window=window)

loss_learned_metric_deep = pe.get_information_loss(data_gt=day_profile,
                                              data_sanitized=sanitized_profile_deep.round(),
                                              window=window)

print("sampled size %s" % subsample_size)
print("information loss with learned metric deep %s and %s" % (loss_learned_metric_deep, loss_learned_metric))








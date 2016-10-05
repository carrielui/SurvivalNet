__author__ = 'Coco'

from SurvivalAnalysis import SurvivalAnalysis
from lifelines.utils import _naive_concordance_index
import numpy as np
import random
import scipy.io as sio
import os
import tensorflow as tf
import cPickle

random.seed(100)

def trainSurvivalNet (mat_file_path, n_hidden, num_steps, num_shuffles, penaltyLambdaArray, alphaArray, prefix) :
        """ This function is to train SurvivalNet with Tensorflow.
        :type mat_file_path: string
        :param mat_file_path: path to the file that stores data in .mat format
        
        :type n_hidden: integer
        :param n_hidden: number of hidden nodes in a layer
        
        :type num_steps: integer
        :param num_steps: number of iterations to run

        :type num_shuffles: integer
        :param num_shuffles: number of shuffles to run

        :type penaltyLambdaArray: np.float32 array
        :param penaltyLambdaArray: array of lambda (regularization parameters) to train to model

        :type alphaArray: np.float32 array
        :param alphaArray: array of alpha (balancing factor between L1 and L2 in elastic net) to train the model

        :type prefix: string
        :param prefix: prefix of output file that stores all results
        
        """


        p = os.path.join(os.getcwd(), mat_file_path)
        Brain_C = sio.loadmat(p)

        data = Brain_C['Integ_X']
        C = np.asarray([c[0] for c in Brain_C['Censored']])
        survival = np.asarray([t[0] for t in Brain_C['Survival']])

        T = np.asarray([t[0] for t in Brain_C['Survival']])
        X = Brain_C['Integ_X']

        #Use the whole dataset fotr pretraining
        pretrain_set = X

        #foldsize denotes th amount of data used for testing. The same amount 
        #of data is used for model selection. The rest is used for training.
        fold_size = int( len(X) / 10)

        train_set = {}
        test_set = {}
        final_set = {}

        #caclulate the risk group for every patient i: patients who die after i
        sa = SurvivalAnalysis()    
        train_set['X'], train_set['T'], train_set['C'], train_set['A'] = sa.calc_at_risk(X[0:fold_size * 6,], T[0:fold_size * 6], C[0:fold_size * 6]);
        test_set['X'], test_set['T'], test_set['C'], test_set['A'] = sa.calc_at_risk(X[fold_size * 6: fold_size * 8,], T[fold_size * 6: fold_size * 8], C[fold_size * 6: fold_size * 8]);
        final_set['X'], final_set['T'], final_set['C'], final_set['A'] = sa.calc_at_risk(X[fold_size * 8: ,], T[fold_size * 8: ], C[fold_size * 8:]);

        ## initialization
        n_obs = train_set['X'].shape[0] # 302
        n_in = train_set['X'].shape[1] # 201

        test_obs = test_set['X'].shape[0] # 64
        test_in = test_set['X'].shape[1] # 201

        n_out = 1

        #### tensorflow implementation
        def cumsum(x, observations):
                x = tf.reshape(x, (1, observations))
                values = tf.split(1, x.get_shape()[1], x)
                out = []
                prev = tf.zeros_like(values[0])
                for val in values:
                        s = prev + val
                        out.append(s)
                        prev = s
                cumsum = tf.concat(1, out)
                cumsum = tf.reshape(cumsum, (observations, 1))
                return cumsum


        with tf.device('/cpu'):
                ## dropout
                keep_prob = tf.placeholder(tf.float32)
                
                ## penaltyLambda
                penaltyLambda = tf.placeholder(tf.float32)

                ## alpha
                alpha = tf.placeholder(tf.float32)

                ## data
                input = tf.placeholder(tf.float32, [n_obs, n_in])
                at_risk = tf.placeholder(tf.int32, [n_obs, ])
                observed = tf.placeholder(tf.float32, [n_obs, ])
                    
                # testing data
                test_input = tf.placeholder(tf.float32, [test_obs, test_in])
                prediction_at_risk = tf.placeholder(tf.int32, [test_obs, ])
                prediction_observed = tf.placeholder(tf.float32, [test_obs, ])

                ## layer_1
                w_1 = tf.Variable(tf.truncated_normal([n_in, n_hidden], dtype=tf.float32)/20)
                output_layer1 = tf.nn.relu(tf.matmul(input, w_1))
                output_layer1_drop = tf.nn.dropout(output_layer1, keep_prob)
                prediciton_layer1 = tf.nn.relu(tf.matmul(test_input, w_1))

                """ ## layer_2
                w_2 = tf.Variable(tf.truncated_normal([n_hidden, n_hidden], dtype=tf.float32)/20)
                output_layer2 = tf.nn.relu(tf.matmul(output_layer1_drop, w_2))
                output_layer2_drop = tf.nn.dropout(output_layer2, keep_prob)
                prediciton_layer2 = tf.nn.relu(tf.matmul(prediciton_layer1, w_2))
                    
                ## layer_3
                w_3 = tf.Variable(tf.truncated_normal([n_hidden, n_hidden], dtype=tf.float32)/20)
                output_layer3 = tf.nn.relu(tf.matmul(output_layer2_drop, w_3))
                output_layer3_drop = tf.nn.dropout(output_layer3, keep_prob)
                prediciton_layer3 = tf.nn.relu(tf.matmul(prediciton_layer2, w_3))

                ## layer_4
                w_4 = tf.Variable(tf.truncated_normal([n_hidden, n_hidden], dtype=tf.float32)/20)
                output_layer4 = tf.nn.relu(tf.matmul(output_layer3_drop, w_4))
                output_layer4_drop = tf.nn.dropout(output_layer4, keep_prob)
                prediciton_layer4 = tf.nn.relu(tf.matmul(prediciton_layer3, w_4))

                # layer_5
                w_5 = tf.Variable(tf.truncated_normal([n_hidden, n_hidden], dtype=tf.float32)/20)
                output_layer5 = tf.nn.relu(tf.matmul(output_layer4_drop, w_5))
                output_layer5_drop = tf.nn.dropout(output_layer5, keep_prob)
                prediciton_layer5 = tf.nn.relu(tf.matmul(prediciton_layer4, w_5))"""
                

                ## output layer
                w_6 = tf.Variable(tf.truncated_normal([n_hidden, n_out], dtype=tf.float32)/20)
                output = tf.matmul(output_layer1_drop, w_6)

                prediction_output = tf.matmul(prediciton_layer1, w_6)
                   
                exp = tf.reverse(tf.exp(output), dims = [True, False])
                partial_sum_a = cumsum(exp, n_obs)
                partial_sum = tf.reverse(partial_sum_a, dims = [True, False]) + 1
                log_at_risk = tf.log(tf.gather(partial_sum, tf.reshape(at_risk, [-1])) + 1e-50)
                diff = tf.sub(output,log_at_risk)
                times = tf.reshape(diff, [-1]) * observed
                cost = - (tf.reduce_sum(times)) +\
                alpha * tf.reduce_sum(penaltyLambda * tf.nn.l2_loss(w_6)) +\
                alpha * tf.reduce_sum(penaltyLambda * tf.nn.l2_loss(w_1)) +\
                (1 - alpha) * tf.reduce_sum(penaltyLambda * tf.abs(w_6)) +\
                (1 - alpha) * tf.reduce_sum(penaltyLambda * tf.abs(w_1))

                weightSize = tf.nn.l2_loss(w_1) + \
                tf.nn.l2_loss(w_6)


                ### prediction
                prediction_exp = tf.reverse(tf.exp(prediction_output), dims = [True, False])
                prediction_partial_sum_a = cumsum(prediction_exp, test_obs)
                prediction_partial_sum = tf.reverse(prediction_partial_sum_a, dims = [True, False]) + 1
                prediction_log_at_risk = tf.log(tf.gather(prediction_partial_sum, tf.reshape(prediction_at_risk, [-1])) + 1e-50)
                prediction_diff = tf.sub(prediction_output,prediction_log_at_risk)
                prediction_times = tf.reshape(prediction_diff, [-1]) * prediction_observed
                prediction_cost = - (tf.reduce_sum(prediction_times))


                global_step = tf.Variable(0, trainable=False)
                starter_learning_rate = 0.0001
                learning_rate = tf.train.exponential_decay(starter_learning_rate, global_step, 100000, 0.989, staircase=True)

                # optimizer
                optimizer = tf.train.GradientDescentOptimizer(learning_rate).minimize(cost)

        for alphaArrayIndex in range(len(alphaArray)):
                print("alpha: " + str(alphaArray[alphaArrayIndex]))

                for penaltyLambdaIndex in range(len(penaltyLambdaArray)):
                        print("lambda: " + str(penaltyLambdaArray[penaltyLambdaIndex]))
                
                        targetFile = os.path.join(os.getcwd(), prefix) + ".txt"
                 
                        target = open(targetFile, "w")
                        finalTestingAcc = np.zeros(num_shuffles)
                        testingAcc = np.zeros(num_shuffles)

                        bestAccInOneShuffle = np.zeros(num_steps)

                        session = tf.InteractiveSession()

                        for shuffle in range(num_shuffles):
                                test_ci=[]
                                train_ci=[]
                                test_cost=[]
                                train_cost=[]
                                outputPath = os.path.join(os.getcwd(), prefix) + "-" + str(shuffle)

                                tf.initialize_all_variables().run()
                                index = np.arange(data.shape[0])
                                random.shuffle(index)

                                X = X[index, :]
                                C = C[index]
                                T = T[index]
                        
                                fold_size = int( len(X) / 10)
                                
                                train_set = {}
                                test_set = {}
                                final_set = {}
                        
                            
                                sa = SurvivalAnalysis()    
                                train_set['X'], train_set['T'], train_set['C'], train_set['A'] = sa.calc_at_risk(X[0:fold_size * 6,], T[0:fold_size * 6], C[0:fold_size * 6]);
                                test_set['X'], test_set['T'], test_set['C'], test_set['A'] = sa.calc_at_risk(X[fold_size * 6: fold_size * 8,], T[fold_size * 6: fold_size * 8], C[fold_size * 6: fold_size * 8]);
                                #final_set['X'], final_set['T'], final_set['C'], final_set['A'] = sa.calc_at_risk(X[fold_size * 8: fold_size * 10,], T[fold_size * 8:fold_size * 10 ], C[fold_size * 8:fold_size * 10]);

                                number_of_range = 0
                                sum_of_test_c_index = np.zeros(15)
                                for step in range(num_steps):
                                        feed_dict = {input : train_set['X'], at_risk : train_set['A'], observed : 1-train_set['C'], test_input : test_set['X'], prediction_at_risk: test_set['A'], prediction_observed : 1-test_set['C'], keep_prob : .5, penaltyLambda : penaltyLambdaArray[penaltyLambdaIndex], alpha : alphaArray[alphaArrayIndex]}

                                        timesV, _, test_outputV, outputV, costV, expV, partialV, logV, diffV, w1V, costTestV, weightSizeV = session.run([times, optimizer, prediction_output, output, cost, exp, partial_sum, log_at_risk, diff, w_1, prediction_cost, weightSize], feed_dict = feed_dict)
                                        train_c_index = sa.c_index(outputV, train_set['T'], train_set['C'])
                                        train_ci.append(train_c_index)
                                        test_c_index = sa.c_index(test_outputV, test_set['T'], test_set['C'])
                                        test_ci.append(test_c_index)
                                        train_cost.append(costV)
                                        test_cost.append(costTestV)
                                
                                        if (step % 10 == 0) :
                                                print("step: " + str(step) + ", cost: " + str(costV) + ", train cIndex: " + str(train_c_index) + ", test cIndex: " + str(test_c_index))

                                        if (step == num_steps - 1):
                                                print("best result at shuffle "+ str(shuffle) +' ' + str(np.max(test_ci)))
                                                #feed_dict = {input : train_set['X'], at_risk : train_set['A'], observed : 1-train_set['C'], test_input : final_set['X'], keep_prob : 1, penaltyLambda : penaltyLambdaArray[penaltyLambdaIndex], alpha : alphaArray[alphaArrayIndex]}
                                                f1 = open(outputPath+'tst_ci.txt', 'w')
                                                f2 = open(outputPath+'tst_cost.txt', 'w')
                                                f3 = open(outputPath+'trn_ci.txt', 'w')
                                                f4 = open(outputPath+'trn_cost.txt', 'w')

                                                cPickle.dump(test_ci, f1, protocol=cPickle.HIGHEST_PROTOCOL)
                                                cPickle.dump(test_cost, f2, protocol=cPickle.HIGHEST_PROTOCOL)
                                                cPickle.dump(train_ci, f3, protocol=cPickle.HIGHEST_PROTOCOL)
                                                cPickle.dump(train_cost, f4, protocol=cPickle.HIGHEST_PROTOCOL)

#                                                final_outputV = session.run(prediction_output, feed_dict = feed_dict)
#                                                final_c_index = sa.c_index(final_outputV, final_set['T'], final_set['C'])
#                                                finalTestingAcc[shuffle] = final_c_index
                                                testingAcc[shuffle] = test_c_index

#                        target.write("final mean: " + str(np.mean(finalTestingAcc)) + "\n")
#                        target.write("final sd: " + str(np.std(finalTestingAcc)) + "\n")

                        target.write("---\n")

                        target.write("testing mean: " + str(np.mean(testingAcc)) + "\n")
                        target.write("testing sd: " + str(np.std(testingAcc)) + "\n")

                        target.close()
if __name__ == '__main__':
    trainSurvivalNet('data/Brain_Integ.mat', 500,500, 20, [0], [0], 'results/nl1-hs500-do.5')

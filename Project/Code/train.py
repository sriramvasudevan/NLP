import nltk, string, re
from nltk.corpus import stopwords
from sklearn.feature_selection import SelectKBest, chi2
from sklearn.svm import LinearSVC
from nltk.classify.scikitlearn import SklearnClassifier
from nltk.stem.porter import PorterStemmer
from nltk.probability import FreqDist
from sklearn.feature_extraction.text import TfidfTransformer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
import numpy as np 

def wordlist(text):
    return re.findall('[a-z]+', text.lower())

def newwordlist(text):
    initial = re.findall('[a-z]+', text.lower())
    badwords = stopwords.words('english')
    badwords.extend(['ac', 'in', 'iitm', 'www', 'th', 'st', 'll'])
    badwords.extend(list(string.lowercase))
    final = [w for w in initial if w not in badwords]
    return final

def labels_find_intersection(set1, set2):
    num = den = 0
    for label1, label2 in zip(set1, set2):
        if label2 != 'useless':
            den += 1
            if label1==label2:
                num += 1
    return float(num)/den

def tokenize(text):
    return [PorterStemmer().stem(item) for item in nltk.word_tokenize(text)]

def bag_of_words(words):
        return dict([(word, True) for word in words])

def bag_of_words_not_in_set(words, badwords):
    return bag_of_words(set(words) - set(badwords))

def bag_of_non_stopwords(words, stopfile = 'english'):
    badwords = stopwords.words(stopfile)
    badwords.extend(['ac', 'in', 'iitm', 'www', 'th', 'st',])
    badwords.extend(list(string.lowercase))
    return bag_of_words_not_in_set(words, badwords)

def coem(L1, L2, L_labels, U1, U2):
    L1_train = []
    for i,mail in enumerate(L1):
        L1_train.append((bag_of_non_stopwords(wordlist(mail)),L_labels[i]))    
    #classifier1 = nltk.NaiveBayesClassifier.train(L1_train)

    classifier1 = SklearnClassifier(LinearSVC())
    classifier1.train(L1_train)

    # Predict on U using 1st classifier
    U1_bow = []
    for mail in U1:
        U1_bow.append(bag_of_non_stopwords(wordlist(mail)))

    U1_labels = classifier1.classify_many(U1_bow)

    # Trained on A classifier.
    # Now B will learn on L as well as A's labels on U
    iterations = 0

    while iterations < 5:
        L2_train = []
        # Add everything in L
        for i,mail in enumerate(L2):
            L2_train.append((bag_of_non_stopwords(wordlist(mail)),L_labels[i]))
        # Add everything in U with labels from A
        for i,mail in enumerate(U2):
            L2_train.append((bag_of_non_stopwords(wordlist(mail)),U1_labels[i]))

        #classifier2 = nltk.NaiveBayesClassifier.train(L2_train)
        classifier2 = SklearnClassifier(LinearSVC())
        classifier2.train(L2_train)
        U2_bow = []

        for mail in U2:
            U2_bow.append(bag_of_non_stopwords(wordlist(mail)))

        # Now, label U.
        U2_labels = classifier2.classify_many(U2_bow)        

        # Now, classifier 2 has finished labelling everything in U

        # Classifer 1 starts again
        L1_train = []
        # Again , add all mails in L
        for i,mail in enumerate(L1):
            L1_train.append((bag_of_non_stopwords(wordlist(mail)),L_labels[i]))

        # Add all mails in U, but with labels from B. (U2)
        for i,mail in enumerate(U1):
            L1_train.append((bag_of_non_stopwords(wordlist(mail)),U2_labels[i]))

        # Train it
        #classifier1 = nltk.NaiveBayesClassifier.train(L1_train)
        classifier1 = SklearnClassifier(LinearSVC())
        classifier1.train(L1_train)    

        U1_bow = []

        for mail in U1:
            U1_bow.append(bag_of_non_stopwords(wordlist(mail)))

        # Re label it
        U1_labels = classifier1.classify_many(U1_bow)    
        #print U1_labels,U2_labels    
        print labels_find_intersection(U1_labels,U2_labels)
        iterations += 1


    return U1_labels

def cotrain(L1, L2, L_labels, U1, U2):
    ChooseLimit = 1
    iterations = 0
    while len(U1) >0 and len(U2) > 0 and iterations < 20:
        iterations += 1
        L1_train = []
        L2_train = []

        for i,mail in enumerate(L1):
            L1_train.append((bag_of_non_stopwords(wordlist(mail))),L_labels[i])
        
        for i,mail in enumerate(L2):
            L2_train.append((bag_of_non_stopwords(wordlist(mail)),L_labels[i]))
        
        # Created train sets for both classifiers
        # Learn both classifiers
        classifier1 = nltk.NaiveBayesClassifier.train(L1_train)
        classifier2 = nltk.NaiveBayesClassifier.train(L2_train)

        # Predict on U using 1st classifier
        U1_bow = []
        for mail in U1:
            U1_bow.append(bag_of_non_stopwords(wordlist(mail)))

        U1_labels = classifier1.prob_classify_many(U1_bow)
        
        a = {} # a[label] = [ (instance no, prob.) ,..]
        for i,dist in enumerate(U1_labels):    
            for label in dist.samples():
                if label not in a:
                    a[label] = []
                a[label].append((i,dist.prob(label)))
                #print("%s: %f" % (label, dist.prob(label))),

        # Sort desc. on scores
        for label in a:
            a[label].sort(key=lambda x: x[1],reverse = True)

        # Add top- ChooseLimit instances , ensuring prob. > 0.5    
        Entries_to_add = []
        Entries_to_add_indices = []
        for label in a:
            to_add = []
            for entry in a[label][0:ChooseLimit]:
                if entry[1] > 0.5:
                    to_add.append((entry[0],label))
                    Entries_to_add_indices.append(entry[0])

            Entries_to_add.extend(to_add)

        # Entries_to_add has (indices,label) tuples with indices in U1 and U2.
        print len(Entries_to_add)
        for entry in Entries_to_add:
            L1.append(U1[entry[0]])
            L2.append(U2[entry[0]])
            L_labels.append(entry[1])

        U1 = [i for j, i in enumerate(U1) if j not in Entries_to_add_indices]
        U2 = [i for j, i in enumerate(U2) if j not in Entries_to_add_indices]
            
        print len(U1),len(U2),len(L1),len(L2)

        # Predict on U (reduced) using 2nd classifier.
        U2_bow = []
        for mail in U2:
            U2_bow.append(bag_of_non_stopwords(wordlist(mail)))

        U2_labels = classifier2.prob_classify_many(U2_bow)

        a = {} # a[label] = [ (instance no, prob.) ,..]
        for i,dist in enumerate(U2_labels):    
            for label in dist.samples():
                if label not in a:
                    a[label] = []
                a[label].append((i,dist.prob(label)))
                #print("%s: %f" % (label, dist.prob(label))),

        # Sort desc. on scores
        for label in a:
            a[label].sort(key=lambda x: x[1],reverse = True)

        # Add top- ChooseLimit instances , ensuring prob. > 0.5    
        Entries_to_add = []
        Entries_to_add_indices = []
        for label in a:
            to_add = []
            for entry in a[label][0:ChooseLimit]:
                if entry[1] > 0.5:
                    to_add.append((entry[0],label))
                    Entries_to_add_indices.append(entry[0])

            Entries_to_add.extend(to_add)

        # Entries_to_add has (indices,label) tuples with indices in U1 and U2.
        print len(Entries_to_add)
        for entry in Entries_to_add:
            L1.append(U1[entry[0]])
            L2.append(U2[entry[0]])
            L_labels.append(entry[1])
            
        U1 = [i for j, i in enumerate(U1) if j not in Entries_to_add_indices]
        U2 = [i for j, i in enumerate(U2) if j not in Entries_to_add_indices]
            
        print len(U1),len(U2),len(L1),len(L2)
    return L_labels


# Code starts here

all_mails = []
all_mails_subs = []
all_mail_labels = []

with open('Mails/filenames.txt') as f:
    for filename in f.read().splitlines():
        with open('Mails/'+filename) as g:
            all_mails.append(g.read())
            
with open('Subjects/filenames.txt') as f:
    for filename in f.read().splitlines():
        with open('Subjects/'+filename) as g:
            all_mails_subs.append(g.read())
            
a = {}
b = {}

with open('Mail_labels.txt') as f:
    for label in f.read().splitlines():
        all_mail_labels.append(label)
        a[label] = 5
        b[label] = 0

# Finished reading all mails

train_mails = []
train_subs = []
train_mails_labels = []

unlabel_mails = []
unlabel_subs = []
unlabel_mails_labels = []

for mail, label, sub in zip(all_mails, all_mail_labels, all_mails_subs):
    if b[label] < a[label]:
        train_mails.append(mail)
        train_subs.append(sub)
        train_mails_labels.append(label)
        b[label] += 1
    else:
        unlabel_mails.append(mail)
        unlabel_mails_labels.append(label)
        unlabel_subs.append(sub)

#predicted_labels = cotrain(train_mails, train_subs, train_mails_labels, unlabel_mails, unlabel_subs)
#print "Accuracy",labels_find_intersection(predicted_labels,all_mail_labels)

#predicted_labels = coem(train_mails, train_subs, train_mails_labels, unlabel_mails, unlabel_subs)
#print "Accuracy", labels_find_intersection(predicted_labels, unlabel_mails_labels)

# Finding accuracy in case of fully supervised case. But accuracy is only on training set.
train_set = {}

for mail, label in zip(all_mails, all_mail_labels):
    if label not in train_set:
        train_set[label] = []
    train_set[label].append(FreqDist(newwordlist(mail)))

pipeline = Pipeline([('tfidf', TfidfTransformer()),
                     ('chi2', SelectKBest(chi2, k=1000)),
                     ('nb', MultinomialNB())])
classif = SklearnClassifier(pipeline)
add_label = lambda lst, lab: [(x, lab) for x in lst]
finalset = []
for label,bow in train_set.iteritems():
    finalset.extend(add_label(bow, label))
classif.train(finalset)

conf = []
for l, bow in train_set.iteritems():
    labels = np.array(classif.classify_many(bow))
    row = []
    for label in train_set:
        row.append((labels==label).sum())
    conf.append(row)

for c in conf:
    print c

diagval = 0
total = 0
for i in range(len(conf)):
    for j in range(len(conf)):
        total += conf[i][j]
        if i==j:
            diagval += conf[i][j]

accuracy = float(diagval)/total
print "Accuracy fully supervised", accuracy
#TODO: Check if BOW model is right

#print labels, all_mail_labels
#print "Accuracy fully supervised ",labels_find_intersection(labels, all_mail_labels)

#l_pos = np.array(classif.classify_many(pos[100:]))
#l_neg = np.array(classif.classify_many(neg[100:]))
#print "Confusion matrix:\n%d\t%d\n%d\t%d" % (
#          (l_pos == 'pos').sum(), (l_pos == 'neg').sum(),
#          (l_neg == 'pos').sum(), (l_neg == 'neg').sum())
#
#transformer = TfidfTransformer()
#tfidf = transformer.fit_transform(counts)
#print tfidf.shape
##x =  tfs.toarray()
#
##print tfs[1]
#
##train_set = tfs[0].tolist()
#
##print train_set[0]
#
#classifier = SklearnClassifier(LinearSVC())
#classifier.train(train_set)
#
#
##ch2 = SelectKBest(chi2, k=100)
##X_train = ch2.fit_transform(tfidf, all_mail_labels)
###X_test = ch2.transform(X_test)
##print X_train
#
#newclassifier = SklearnClassifier(LinearSVC())
#newclassifier.train(tfidf)
#labels = newclassifier.classify_many(tfidf.to_array())
#print "Accuracy tfidf ",labels_find_intersection(labels,all_mail_labels)
#
##classifier = nltk.NaiveBayesClassifier.train(train_set)
#
#bow = []
#for mail in all_mails:
#    bow.append(bag_of_non_stopwords(wordlist(mail)))
#
#labels = classifier.classify_many(bow)
#
##print len(labels),len(all_mail_labels)
##print labels,all_mail_labels
#print "Accuracy fully supervised ",labels_find_intersection(labels,all_mail_labels)
##classifier.show_most_informative_features()

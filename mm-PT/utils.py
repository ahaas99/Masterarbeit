"""
xAILab
Chair of Explainable Machine Learning
Otto-Friedrich University of Bamberg

@description:
Helper functions.
"""
import torch
import numpy
import random
import numpy as np
from copy import deepcopy
from tqdm import tqdm
from scipy import stats
from sklearn.metrics import accuracy_score
from sklearn.metrics import roc_auc_score
from sklearn.metrics import balanced_accuracy_score
from sklearn.metrics import cohen_kappa_score
from sklearn.metrics import precision_score
from medmnist.evaluator import getACC, getAUC



"""
xAILab
Chair of Explainable Machine Learning
Otto-Friedrich University of Bamberg

@description:
Helper functions.
"""


def seed_worker(worker_id):
    """Set the seed for the current worker."""
    worker_seed = torch.initial_seed() % 2**32
    numpy.random.seed(9930641)
    random.seed(9930641)


def calculate_passed_time(start_time, end_time):
    """
    Calculate the time needed for running the code

    :param: start_time: Start time.
    :param: end_time: End time.
    :return: Duration in hh:mm:ss.ss
    """

    # Calculate the duration
    elapsed_time = end_time - start_time
    hours, rem = divmod(elapsed_time, 3600)
    minutes, seconds = divmod(rem, 60)

    # Return the duration in hours, minutes and seconds
    return int(hours), int(minutes), seconds


def extract_embeddings(model, device, dataloader):
    """
    Extracts the embeddings from the model.

    :param model: Model.
    :param device: Device.
    :param dataloader: Dataloader.
    """
    embeddings_db, labels_db = [], []

    with torch.no_grad():
        for extracted in tqdm(dataloader):
            images, labels = extracted
            images = images.to(device)

            output = model.forward_features(images)
            output = model.forward_head(output, pre_logits=True)
            output = output.reshape(output.shape[0], -1)

            labels_db.append(deepcopy(labels.cpu().numpy()))
            embeddings_db.append(deepcopy(output.cpu().numpy()))

    data = {
        'embeddings': np.concatenate(embeddings_db, axis=0),
        'labels': np.concatenate(labels_db, axis=0),
    }

    return data


def extract_embeddings_densenet(model, device, dataloader):
    """
    Extracts the embeddings from the DenseNet.

    :param model: Model.
    :param device: Device.
    :param dataloader: Dataloader.
    """
    embeddings_db, labels_db = [], []

    with torch.no_grad():
        for extracted in tqdm(dataloader):
            images, labels = extracted
            images = images.to(device)

            output = model.forward_features(images)
            output = model.global_pool(output)
            output = output.reshape(output.shape[0], -1)

            labels_db.append(deepcopy(labels.cpu().numpy()))
            embeddings_db.append(deepcopy(output.cpu().numpy()))

    data = {
        'embeddings': np.concatenate(embeddings_db, axis=0),
        'labels': np.concatenate(labels_db, axis=0),
    }

    return data


def extract_embeddings_alexnet(model, device, dataloader):
    """
    Extracts the embeddings from the AlexNet.

    :param model: Model.
    :param device: Device.
    :param dataloader: Dataloader.
    """
    embeddings_db, labels_db = [], []

    with torch.no_grad():
        for extracted in tqdm(dataloader):
            images, labels = extracted
            images = images.to(device)

            output = model(images)
            output = output.reshape(output.shape[0], -1)

            labels_db.append(deepcopy(labels.cpu().numpy()))
            embeddings_db.append(deepcopy(output.cpu().numpy()))

    data = {
        'embeddings': np.concatenate(embeddings_db, axis=0),
        'labels': np.concatenate(labels_db, axis=0),
    }

    return data


def knn_majority_vote(nbrs, embeddings, support_set_labels, task):
    """
    Finds the k nearest neighbors for each embedding in "embeddings" and performs a majority vote on their labels.
    """

    # Find the k nearest neighbors for each embedding in "embeddings"
    distances, indices = nbrs.kneighbors(embeddings)

    # For each set of k nearest neighbors, find the majority class
    outputs = []
    for neighbors in indices:
        if task == "multi-label, binary-class":
            classes = np.array([support_set_labels[i] for i in neighbors])
            majority_classes = np.mean(classes, axis=0) > 0.5  # Majority vote for each class
            outputs.append(majority_classes)

        else:
            classes = [support_set_labels[i] for i in neighbors]
            majority_class = stats.mode(classes)[0][0]
            outputs.append(majority_class)

    outputs = torch.from_numpy(np.array(outputs))
    outputs = outputs.reshape(outputs.shape[0], -1)

    return outputs


def get_ACC(y_true: np.ndarray, y_pred: np.ndarray, task: str, threshold=0.5):
    """
    Calculates the accuracy of the prediction.

    :param y_true: True labels.
    :param y_pred: Predicted labels.
    :param task: Type of classification task.
    :return: Accuracy
    """

    if task == "multi-label, binary-class":
        y_pre = y_pred > threshold
        acc = 0
        for label in range(y_true.shape[1]):
            label_acc = accuracy_score(y_true[:, label], y_pre[:, label])
            acc += label_acc
        ret = acc / y_true.shape[1]
    elif task == "binary-class":
        if y_pred.ndim == 2:
            y_pred = y_pred[:, -1]
        else:
            assert y_pred.ndim == 1
        ret = accuracy_score(y_true, y_pred > threshold)
    else:
        ret = accuracy_score(y_true, np.array(np.argmax(y_pred, axis=-1)))

    return ret


def get_AUC(y_true: np.ndarray, y_pred: np.ndarray, task: str):
    """
    Calculates the Area-under-the-ROC curve of the prediction.

    :param y_true: True labels.
    :param y_pred: Predicted labels.
    :param task: Type of classification task.
    :return: AUC score.
    """

    if task == "multi-label, binary-class":
        auc = 0
        for i in range(y_pred.shape[1]):
            label_auc = roc_auc_score(y_true[:, i], y_pred[:, i])
            auc += label_auc
        ret = auc / y_pred.shape[1]
    elif task == "binary-class":
        if y_pred.ndim == 2:
            y_pred = y_pred[:, -1]
        else:
            assert y_pred.ndim == 1
        ret = roc_auc_score(y_true, y_pred)
    else:
        auc = 0
        for i in range(y_pred.shape[1]):
            y_true_binary = (y_true == i).astype(float)
            y_score_binary = y_pred[:, i]
            auc += roc_auc_score(y_true_binary, y_score_binary)
        ret = auc / y_pred.shape[1]

    return ret


def get_ACC_kNN(y_true: np.ndarray, y_pred: np.ndarray, task: str):
    """
    Calculates the accuracy of the prediction adapted for the kNN approach.

    :param y_true: True labels.
    :param y_pred: Predicted labels.
    :param task: Type of classification task.
    :return: Accuracy
    """

    if task == "multi-label, binary-class":
        acc = 0
        for label in range(y_true.shape[1]):
            label_acc = accuracy_score(y_true[:, label], y_pred[:, label])
            acc += label_acc
        ret = acc / y_true.shape[1]

    else:
        ret = accuracy_score(y_true, y_pred)

    return ret

def get_AUC_kNN(y_true: np.ndarray, y_pred: np.ndarray, task: str):
    """
    Calculates the accuracy of the prediction adapted for the kNN approach.

    :param y_true: True labels.
    :param y_pred: Predicted labels.
    :param task: Type of classification task.
    :return: Accuracy
    """
    if task == "multi-label, binary-class":
        y_pred = np.transpose([pred[:, 1] for pred in y_pred])
        ret = roc_auc_score(y_true, y_pred)
    elif task == "binary-class":
        ret = roc_auc_score(y_true, y_pred[:, 1])
    else:
        ret = roc_auc_score(y_true, y_pred, multi_class='ovr')
    return ret

def get_Balanced_ACC(y_true: np.ndarray, y_pred: np.ndarray, task: str, threshold=0.5):
    """
    Calculates the accuracy of the prediction adapted for the kNN approach.

    :param y_true: True labels.
    :param y_pred: Predicted labels.
    :param task: Type of classification task.
    :return: Accuracy
    """
    if task == "multi-label, binary-class":
        y_pre = y_pred > threshold
        acc = 0
        for label in range(y_true.shape[1]):
            label_acc = balanced_accuracy_score(y_true[:, label], y_pre[:, label])
            acc += label_acc
        ret = acc / y_true.shape[1]
    elif task == "binary-class":
        if y_pred.ndim == 2:
            y_pred = y_pred[:, -1]
        else:
            assert y_pred.ndim == 1
        ret = balanced_accuracy_score(y_true, y_pred > threshold)
    else:
        ret = balanced_accuracy_score(y_true,  np.array(np.argmax(y_pred, axis=-1)))

    return ret


def get_Cohen_kNN(y_true: np.ndarray, y_pred: np.ndarray, task: str):
    """
    Calculates the accuracy of the prediction adapted for the kNN approach.

    :param y_true: True labels.
    :param y_pred: Predicted labels.
    :param task: Type of classification task.
    :return: Accuracy
    """

    if task == "multi-label, binary-class":
        acc = 0
        for label in range(y_true.shape[1]):
            label_acc = cohen_kappa_score(y_true[:, label], y_pred[:, label])
            acc += label_acc
        ret = acc / y_true.shape[1]

    else:
        ret = cohen_kappa_score(y_true, y_pred)

    return ret

def get_Cohen(y_true: np.ndarray, y_pred: np.ndarray, task: str, threshold=0.5):
    if task == "multi-label, binary-class":
        y_pre = y_pred > threshold
        acc = 0
        for label in range(y_true.shape[1]):
            label_acc = cohen_kappa_score(y_true[:, label], y_pre[:, label])
            acc += label_acc
        ret = acc / y_true.shape[1]
    elif task == "binary-class":
        if y_pred.ndim == 2:
            y_pred = y_pred[:, -1]
        else:
            assert y_pred.ndim == 1
        ret = cohen_kappa_score(y_true, y_pred > threshold)
    else:
        ret = cohen_kappa_score(y_true,  np.array(np.argmax(y_pred, axis=-1)))

    return ret

def get_Precision_kNN(y_true: np.ndarray, y_pred: np.ndarray, task: str):
    """
    Calculates the accuracy of the prediction adapted for the kNN approach.

    :param y_true: True labels.
    :param y_pred: Predicted labels.
    :param task: Type of classification task.
    :return: Accuracy
    """

    if task == "multi-label, binary-class":
        acc = 0
        for label in range(y_true.shape[1]):
            label_acc = precision_score(y_true[:, label], y_pred[:, label])
            acc += label_acc
        ret = acc / y_true.shape[1]

    else:
        ret = precision_score(y_true, y_pred, average='macro')

    return ret

def get_Precision(y_true: np.ndarray, y_pred: np.ndarray, task: str, threshold=0.5):
    if task == "multi-label, binary-class":
        y_pre = y_pred > threshold
        acc = 0
        for label in range(y_true.shape[1]):
            label_acc = precision_score(y_true[:, label], y_pre[:, label])
            acc += label_acc
        ret = acc / y_true.shape[1]
    elif task == "binary-class":
        if y_pred.ndim == 2:
            y_pred = y_pred[:, -1]
        else:
            assert y_pred.ndim == 1
        ret = precision_score(y_true, y_pred > threshold, pos_label=1)
    else:
        ret = precision_score(y_true,  np.array(np.argmax(y_pred, axis=-1)), average='macro')

    return ret
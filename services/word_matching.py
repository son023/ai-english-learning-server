from . import word_metrics
import numpy as np
from string import punctuation
from dtwalign import dtw_from_distance_matrix
import time
from typing import List, Tuple
#from ortools.sat.python import cp_model

offset_blank = 1
TIME_THRESHOLD_MAPPING = 5.0


def get_word_distance_matrix(words_estimated: list, words_real: list) -> np.ndarray:
    number_of_real_words = len(words_real)
    number_of_estimated_words = len(words_estimated)

    word_distance_matrix = np.zeros(
        (number_of_estimated_words+offset_blank, number_of_real_words))
    for idx_estimated in range(number_of_estimated_words):
        for idx_real in range(number_of_real_words):
            word_distance_matrix[idx_estimated, idx_real] = word_metrics.edit_distance_python(
                words_estimated[idx_estimated], words_real[idx_real])

    if offset_blank == 1:
        for idx_real in range(number_of_real_words):
            word_distance_matrix[number_of_estimated_words,
                                 idx_real] = len(words_real[idx_real])
    return word_distance_matrix

def get_best_mapped_words_dtw(words_estimated: list, words_real: list): 
    word_distance_matrix = get_word_distance_matrix(words_estimated, words_real) 
    dtw_result = dtw_from_distance_matrix(word_distance_matrix) 
    real_indices = dtw_result.path[:-1, 1] 
    estimated_indices = dtw_result.path[:-1, 0] 
    mapped_words = ['-'] * len(words_real) 
    mapped_words_indices = [-1] * len(words_real) 
    # Track các est_idx đã được gán để tránh assign nhiều lần 
    est_idx_assigned = set() # Gom nhóm theo real_idx 
    real_to_est_map = {} 
    for real_idx, est_idx in zip(real_indices, estimated_indices): 
        if est_idx < len(words_estimated): 
            real_to_est_map.setdefault(real_idx, []).append(est_idx) 
    for real_idx in range(len(words_real)): 
        if real_idx in real_to_est_map: 
            candidates = real_to_est_map[real_idx] # Loại bỏ duplicate trong candidates 
            unique_candidates = list(set(candidates)) # Trong trường hợp chỉ còn 1 candidate không bị assign 
            available_candidates = [c for c in unique_candidates if c not in est_idx_assigned] 
            if len(available_candidates) == 0: # Không còn candidate nào chưa assign, giữ '-' 
                continue 
            if len(available_candidates) == 1: 
                best_est_idx = available_candidates[0] 
            else: 
                best_error = float('inf') 
                best_est_idx = available_candidates[0] 
                for est_idx in available_candidates: 
                    error = word_metrics.edit_distance_python(words_estimated[est_idx].lower(), words_real[real_idx].lower()) 
                    if error < best_error: 
                        best_error = error 
                        best_est_idx = est_idx 
            mapped_words[real_idx] = words_estimated[best_est_idx] 
            mapped_words_indices[real_idx] = best_est_idx 
            est_idx_assigned.add(best_est_idx) 
    return mapped_words, mapped_words_indices
# coding=utf-8

import os
import pandas as pd
from random import uniform

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
import sys
from numpy.linalg import LinAlgError

from profile.fusion_param import get_fusion_param, ctrl_msg
from util.file_helper import read_lines_and, read_lines

# data type :
# 0: market1501 real data, 1: market1501 predict top10 data,
# 2: grid true data, 3: grid predict data,
# 4: grid rand data
# 5: 3dpes data
from util.viz import draw_line

data_type = 1

camera_cnt = 6

viz_local = True


def track_infos(fusion_param, camera_num, s_num):
    # fusion_param = get_fusion_param()
    camera_num = str(camera_num)
    tracks = list()

    def count_interval(img_name):
        # 字符串转track信息，包含person id（即图片id），seq num，track time（时间点，不是时间差）
        if '.' not in img_name:
            return
        track_info = img_name.split('.')[0].split('_')
        person_id = track_info[0]
        track_time = int(track_info[2])
        seq_num = int(track_info[1][3])
        if seq_num == s_num:
            tracks.append([person_id, track_time])

    # 现在data_type 1已经能处理所有情况了
    if data_type == 0:
        # read_lines_and('market_s1/track_c%ds1.txt' % camera_num, count_interval)
        read_lines_and(fusion_param['predict_camera_path'] + camera_num + '.txt', count_interval)
    elif data_type == 2:
        # read_lines_and('grid/trackc%d.txt' % camera_num, count_interval)
        read_lines_and(fusion_param['predict_camera_path'] + camera_num + '.txt', count_interval)
    elif data_type == 3:
        read_lines_and('grid_predict/grid_c%d.txt' % camera_num, count_interval)
        read_lines_and(fusion_param['predict_camera_path'] + camera_num + '.txt', count_interval)
    elif data_type == 4:
        # read_lines_and('grid_predict/rand/grid_c%d.txt' % camera_num, count_interval)
        read_lines_and(fusion_param['predict_camera_path'] + camera_num + '.txt', count_interval)
    elif data_type == 5:
        # read_lines_and('3dpes/c%d_tracks.txt' % camera_num, count_interval)
        read_lines_and(fusion_param['predict_camera_path'] + camera_num + '.txt', count_interval)
    else:
        if os.path.exists(fusion_param['predict_camera_path'] + camera_num + '.txt'):
            read_lines_and(fusion_param['predict_camera_path'] + camera_num + '.txt', count_interval)

    return tracks


def find_id_delta(intervals, id, frame):
    # if we find the smallest delta, the distribution of tracks will be different
    frame = int(frame)
    deltas = list()
    for interval in intervals:
        if interval[0] == id:
            # 首先要person id一致，然后计算时间差
            deltas.append(frame - interval[1])
        else:
            continue
    return deltas


def camera_distribute(fusion_param, camera_num):
    # 左图中的人在右图可能出现在6个摄像头中
    deltas = [list() for i in range(camera_cnt)]
    # market1501数据集有六个序列，只有同一个序列才能计算delta
    seq_s = [1, 2, 3, 4, 5, 6]
    # 每个序列统计一遍deltas，合并到总的deltas中
    for i in range(len(seq_s)):
        # 得到右图的时空信息和人物信息6×[time, pid]*n
        intervals = track_infos(fusion_param, camera_num, seq_s[i])

        # print('get intervals for c%d' % camera_num)

        def shuffle_person(img_name):
            if '.' not in img_name:
                return
            track_info = img_name.split('.')[0].split('_')
            person_id = track_info[0]
            # 每个左图统计一遍deltas，合并到总的deltas中
            track_deltas = find_id_delta(intervals, person_id, int(track_info[2]))
            if data_type == 2 or data_type == 3 or data_type == 4:
                camera_id = int(track_info[1])
            else:
                camera_id = int(track_info[1][1])
            if len(track_deltas) == 0:
                return
            for delta in track_deltas:
                if person_id != 0:
                    # exclude first zero record and not found id records
                    # deltas.append([cur_delta['id'], cur_delta['camera'], cur_delta['delta']])
                    # ignore large data
                    if abs(delta) < 1000000:
                        deltas[camera_id - 1].append(delta)

        # data type为1足够应对所有情况，
        # shuffle person实际上是根据person id是否对应来决定是否计算时间差，并最终返回6串时间差
        if data_type == 0:
            # read_lines_and('market_s1/track_s1.txt', shuffle_person)
            read_lines_and(fusion_param['predict_track_path'], shuffle_person)
        elif data_type == 2:
            # read_lines_and('grid/tracks.txt', shuffle_person)
            read_lines_and(fusion_param['predict_track_path'], shuffle_person)
        elif data_type == 3 or data_type == 4:
            # read_lines_and('grid_predict/grid_tracks.txt', shuffle_person)
            read_lines_and(fusion_param['predict_track_path'], shuffle_person)
        elif data_type == 5:
            # read_lines_and('3dpes/test_tracks.txt', shuffle_person)
            read_lines_and(fusion_param['predict_track_path'], shuffle_person)
        else:
            read_lines_and(fusion_param['predict_track_path'], shuffle_person)
    return deltas


def viz_data_for_market(fusion_param):
    track_distribute = list()
    # 当左图是camera i时，右图为各个camera的分布
    for i in range(camera_cnt):
        track_distribute.append(camera_distribute(fusion_param, i + 1))
    return track_distribute


def distribute_in_cameras(data_s, subplot, camera_id):
    sns.set(color_codes=True)
    for i, data in enumerate(data_s):
        # if camera_id == i + 1:
        #     continue
        if len(data) == 0:
            print('no data: %d - %d' % (camera_id, i))
            continue
        print("camera %d to camera %d, record number: %d" % (camera_id, i + 1, len(data)))
        print(data)
        try:
            sns.distplot(np.array(data), label='camera %d' % (i + 1), hist=False, ax=subplot,
                         axlabel='Distribution for camera %d' % camera_id)
        except LinAlgError:
            print 'singular matrix'


def viz_market_distribution(fusion_param):
    viz_data = viz_data_for_market(fusion_param)
    f, axes = plt.subplots(camera_cnt / 2, 2, figsize=(15, 10))
    if viz_local:
        for ax_s in axes:
            for ax in ax_s:
                ax.set_xlabel('time')
                ax.set_ylabel('appear density')
                # ax.set_xlim([-2000, 2000])
                # ax.set_ylim([0, 0.025])
    sns.despine(left=True)
    for i in range(camera_cnt):
        # sns.plt.title('Appear distribution in cameras %d' % (i + 1))
        distribute_in_cameras(viz_data[i], axes[i / 2, i % 2], i + 1)
        print('viz camera %d' % (i + 1))
    sns.plt.show()


def deltas2track(fusion_param):
    viz_data = viz_data_for_market(fusion_param)
    track = [[list(), list()] for _ in range(camera_cnt)]
    for i, camera_deltas in enumerate(viz_data):
        for j, per_camera_deltas in enumerate(camera_deltas):
            for delta in per_camera_deltas:
                track[i][0].append(j + 1 + uniform(-0.2, 0.2))
                track[i][1].append(delta)
    return track


def distribute_joint(data_s, subplot, camera_id):
    if len(data_s[0]) < 5:
        supply_cnt = (5 - len(data_s[0])) / len(data_s[0]) + 1
        for _ in range(supply_cnt):
            data_s[0] += data_s[0]
            data_s[1] += data_s[1]
    sns.kdeplot(np.array(data_s[0]), np.array(data_s[1]), shade=True, bw="silverman", ax=subplot, cmap="Purples")
    # subplot.scatter(data_s[0], data_s[1], s=10, c='g', marker='o')


def viz_market(fusion_param):
    viz_data = deltas2track(fusion_param)
    f, axes = plt.subplots(camera_cnt / 2, 2)
    if viz_local:
        for i, ax_s in enumerate(axes):
            for j, ax in enumerate(ax_s):
                ax.set_title('Distribution for camera %d' % (i * 2 + j + 1))
                # ax.set_xlabel('camera')
                ax.set_ylabel('time')
                if data_type <= 1 or data_type > 4:
                    ax.set_ylim([-500, 500])
    sns.despine(left=True)
    for i in range(camera_cnt):
        # sns.plt.title('Appear distribution in cameras %d' % (i + 1))
        if len(viz_data[i][0]) == 0:
            print('no data for camera %d' % (i + 1))
            continue
        distribute_joint(viz_data[i], axes[i / 2, i % 2], i + 1)
        print('viz camera %d' % (i + 1))
    sns.plt.show()


def prob_curve(x_s, y_s):
    plt.plot(x_s, y_s)


def viz_fusion_curve(delta_range, probs_s):
    for probs in probs_s:
        for i in range(camera_cnt):
            for j in range(camera_cnt):
                if len(probs[i][j]) == 0:
                    continue
                plt.subplot(3, 2, i + 1)
                plt.plot(delta_range, probs[i][j], label='camera%d' % (j + 1))
                plt.legend(loc=3)
            print('viz camera %d' % (i + 1))
        sns.plt.show()


def viz_heat_map(pt):
    # f, ax = plt.subplots(figsize=(15, 15))
    f, ax = plt.subplots()
    # cmap = sns.color_palette("coolwarm", 7)
    cmap = sns.cubehelix_palette(n_colors=8, start=3, rot=0.7, dark=0.4, light=0.92, gamma=1.0, hue=2.5, as_cmap=True)
    sns.heatmap(pt, cmap=cmap, linewidths=0.0, ax=ax, annot=True, fmt='.3f')
    ax.set_title('Transfer heat map on Market1501')
    ax.set_xlabel('transfer time')
    ax.set_ylabel('camera_pair')
    sns.plt.show()
    f.savefig('sns_heatmap_normal.jpg', bbox_inches='tight')


def viz_gray_map(pt):
    f, ax = plt.subplots()
    # cmap = sns.color_palette("coolwarm", 7)
    sns.set(font_scale=2.5)
    cmap = sns.cubehelix_palette(n_colors=8, start=3, rot=0.7, dark=0.4, light=0.92, gamma=1.0, hue=0, as_cmap=True)
    sns.heatmap(pt, cmap=cmap, linewidths=0.0, ax=ax, annot=True, fmt='.3f')
    ax.set_title('')
    print sys.getdefaultencoding()
    reload(sys)
    sys.setdefaultencoding('utf8')
    ax.set_xlabel('α', fontsize=32)
    ax.set_ylabel('β', fontsize=32)
    ax.invert_yaxis()
    plt.yticks(fontsize=32)
    plt.xticks(fontsize=32)
    sns.plt.show()
    f.savefig('sns_gray.jpg', bbox_inches='tight')


def gray_data(values):
    # market
    df = pd.DataFrame({'a': [0.0, 0.0, 0.0, 0.0, 0.25, 0.25, 0.25, 0.5, 0.5, 0.75],
                       'b': [0.0, 0.25, 0.5, 0.75, 0.0, 0.25, 0.5, 0.0, 0.25, 0.0],
                       'values': values})
    pt = df.pivot_table(index='a', columns='b', values='values', aggfunc=np.sum)
    return pt


def iter_acc_data(data_path):
    lines = read_lines(data_path)
    cv_accs = list()
    acc_cnt = 0
    cv_cnt = -1
    for i, line in enumerate(lines):
        if i % 2 == 0:
            continue
        if (i - 1) % 44 == 0:
            cv_cnt += 1
            cv_accs.append([list(), list()])
        if acc_cnt % 2 == 0:
            cv_accs[cv_cnt][0].append(float(line.split()[0]))
        else:
            cv_accs[cv_cnt][1].append(float(line.split()[0]))
        acc_cnt += 1

    avg_accs = np.array(cv_accs).mean(axis=0)
    return avg_accs


def sensitivity_eval():
    grid_sensity_values = list()
    lines = read_lines('../post_process/market_sense.txt')
    rank1_accs = list()
    cur_cv = -1
    for i, line in enumerate(lines):
        if i % 20 == 0:
            rank1_accs.append(list())
            cur_cv += 1
        if i % 2 == 0:
            continue
        rank1_accs[cur_cv].append(float(line.split()[0]))
    grid_avg_accs = np.array(rank1_accs).mean(axis=0)
    market_values = [0.740202, 0.746437, 0.746140, 0.745843, 0.739311, 0.745843, 0.746140, 0.739905,
                     0.746734, 0.739311]
    viz_gray_map(gray_data(grid_avg_accs))


if __name__ == '__main__':
    # distribution visualization
    # ctrl_msg['data_folder_path'] = 'market_market-test'
    # fusion_param = get_fusion_param()
    # viz_market_distribution(fusion_param)
    # viz_market(fusion_param)
    # sns.palplot(sns.cubehelix_palette(n_colors=8, start=3, rot=0.7, dark=0.4, light=0.8, gamma=1.0, hue=0))
    # sns.plt.show()
    # multi iteration result
    accs = iter_acc_data('../post_process/grid_market_iter.txt')
    # accs = iter_acc_data('../post_process/market_grid_iter.txt')
    draw_line(accs, np.arange(0, len(accs[0])), 'Rank-1 precision', 'Number of iterations', ['Visual Classifier C', 'Fusion Model F'], title='')
    # #sensitivity result
    # sensitivity_eval()

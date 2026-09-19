import os
import pm4py
import sys
import itertools
from bisect import bisect_right
from PyQt6.QtWidgets import *
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import *
from collections import defaultdict, deque

if getattr(sys, "frozen", False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

sys.path.append(os.path.join(BASE_DIR, "graphicsviz"))
from episode_visualizer import EpisodeVisualizer
from converter import Converter
from theme import detect_theme, build_stylesheet
from itertools import product

CASE_COL = "case:concept:name"
ACTIVITY_COL = "concept:name"
MAX_SPAN_FACTOR = 1  # n + 1 (Window size dependent on activity count)

XES_LOCATION = ""
EPS = []
EPSFILE = ""

def clamp01(value):
    if value < 0:
        return 0.0
    if value > 1:
        return 1.0
    return value

class ProbabilisticDependency(QThread):
    log = None
    episodes = None
    freq = None
    result = pyqtSignal(object)
    def setFrequencies(self,freq):
        self.freq = freq
    def getFrequencies(self):
        return self.freq
    def setLog(self,log):
        self.log = log
    def getLog(self):
        return self.log
    def setEpisodes(self,episodes):
        self.episodes = episodes
    def getEpisodes(self):
        return self.episodes
    
    def run(self):
        try:
            ret = self.evalProbabilisticDependency()
        except Exception:
            import traceback
            traceback.print_exc()
            ret = []
        self.result.emit(ret)
    def stop(self):
        pass

    def setOccurrenceSets(self, occ):
        self.occurrence_sets = occ

    def evalProbabilisticDependency(self):
        episodes = self.getEpisodes()
        occ_sets = self.occurrence_sets

        keyed = []
        for ep in episodes:
            key = (tuple(ep[0]), tuple(sorted(ep[1])))
            occ_list = occ_sets.get(key, [])
            keyed.append((ep, {t[0] for t in occ_list}))

        results = []

        for (ep1, s1), (ep2, s2) in itertools.combinations(keyed, 2):
            if not s1 or not s2:
                continue

            if s1.isdisjoint(s2):
                continue

            both = len(s1 & s2)
            dep_2_given_1 = clamp01(both / len(s1))
            dep_1_given_2 = clamp01(both / len(s2))

            if dep_2_given_1 > 0:
                results.append(("Dependency", ep1, ep2, dep_2_given_1))

            if dep_1_given_2 > 0:
                results.append(("Dependency", ep2, ep1, dep_1_given_2))

        return results

class Structuredness(QThread):
    global CASE_COL
    global ACTIVITY_COL
    log = None
    episodes = None
    freq = None
    result = pyqtSignal(object)
    def setFrequencies(self,freq):
        self.freq = freq
    def getFrequencies(self):
        return self.freq
    def setLog(self,log):
        self.log = log
    def getLog(self):
        return self.log
    def setEpisodes(self,episodes):
        self.episodes = episodes
    def getEpisodes(self):
        return self.episodes
    
    def run(self):
        try:
            ret = self.evalStructuredness()
        except Exception:
            import traceback
            traceback.print_exc()
            ret = []
        self.result.emit(ret)
    def stop(self):
        pass
    def evalStructuredness(self):
        df = self.getLog()
        grouped = df.groupby(CASE_COL)[ACTIVITY_COL].apply(list)
        log = grouped.tolist()

        activities = set()
        for trace in log:
            activities.update(trace)

        N = len(activities)
        if N <= 1:
            return []

        preset = defaultdict(set)
        postset = defaultdict(set)

        for trace in log:
            for i, act in enumerate(trace):
                if i > 0:
                    preset[act].add(trace[i-1])
                if i < len(trace) - 1:
                    postset[act].add(trace[i+1])

        output = []
        for a in sorted(activities):
            pre_size = len(preset[a])
            post_size = len(postset[a])

            tau_pre = 1.0 if pre_size <= 1 else 1 - ((pre_size) / (N - 1))
            tau_post = 1.0 if post_size <= 1 else 1 - ((post_size) / (N - 1))
            tau_avg = (tau_pre + tau_post) / 2

            output.append((
                "STRUCT",
                a,
                {
                    "preset": preset[a],
                    "postset": postset[a],
                    "tau_pre": tau_pre,
                    "tau_post": tau_post,
                    "tau_avg": tau_avg
                }
            ))

        return output

class AbsoluteConnection(QThread):
    log = None
    episodes = None
    freq = None
    result = pyqtSignal(object)

    def setFrequencies(self,freq):
        self.freq = freq
    def getFrequencies(self):
        return self.freq
    def setLog(self,log):
        self.log = log
    def getLog(self):
        return self.log
    def setEpisodes(self,episodes):
        self.episodes = episodes
    def getEpisodes(self):
        return self.episodes
    
    def run(self):
        try:
            ret = self.findConnections()
        except Exception:
            import traceback
            traceback.print_exc()
            ret = []
        self.result.emit(ret)
    def stop(self):
        pass

    def setOccurrenceSets(self, occ):
        self.occurrence_sets = occ

    def findConnections(self):
        episodes = self.getEpisodes()
        occ_sets = self.occurrence_sets

        keyed = []
        for ep in episodes:
            key = (tuple(ep[0]), tuple(sorted(ep[1])))
            occ_list = occ_sets.get(key, [])
            keyed.append((ep, {t[0] for t in occ_list}))


        results = []
        n = len(keyed)
        expected_pairs = n * (n - 1) // 2
        evaluated_pairs = 0

        for i in range(n):
            ep_i, s1 = keyed[i]
            if not s1:
                evaluated_pairs += (n - 1 - i)
                continue

            for j in range(i + 1, n):
                ep_j, s2 = keyed[j]
                evaluated_pairs += 1
                if not s2:
                    continue

                if s1.isdisjoint(s2):
                    continue

                shared_n = len(s1 & s2)
                union_n = len(s1) + len(s2) - shared_n
                tau = clamp01(shared_n / union_n)

                if tau > 0:
                    results.append(("Co-occurrence", ep_i, ep_j, tau))

        return results
                  
class AbsoluteExclusion(QThread):
    log = None
    episodes = None
    freq = None
    result = pyqtSignal(object)
    def setFrequencies(self,freq):
        self.freq = freq
    def getFrequencies(self):
        return self.freq
    def setLog(self,log):
        self.log = log
    def getLog(self):
        return self.log
    def setEpisodes(self,episodes):
        self.episodes = episodes
    def getEpisodes(self):
        return self.episodes
    
    def run(self):
        try:
            ret = self.findExclusions()
        except Exception:
            import traceback
            traceback.print_exc()
            ret = []
        self.result.emit(ret)
    def stop(self):
        pass
    
    def setOccurrenceSets(self, occ):
        self.occurrence_sets = occ

    def findExclusions(self):

        episodes = self.getEpisodes()
        occ_sets = self.occurrence_sets
        keyed = []
        for ep in episodes:
            key = (tuple(ep[0]), tuple(sorted(ep[1])))
            occ_list = occ_sets.get(key, [])
            keyed.append((ep, {t[0] for t in occ_list}))


        results = []
        n = len(keyed)
        expected_pairs = n * (n - 1) // 2
        evaluated_pairs = 0

        for i in range(n):
            ep1, s1 = keyed[i]

            for j in range(i + 1, n):
                ep2, s2 = keyed[j]
                evaluated_pairs += 1

                union_n = len(s1) + len(s2) - len(s1 & s2)
                if not union_n:
                    continue
                shared_n = len(s1 & s2)
                xor_n = len(s1) + len(s2) - 2 * shared_n
                percentage = clamp01(xor_n / union_n)

                if percentage > 0:
                    results.append(("Exclusion", ep1, ep2, percentage))

        return results

class Subsume(QThread):
    log = None
    episodes = None
    freq = None
    occurrence_sets = {}
    result = pyqtSignal(object)
    def setFrequencies(self,freq):
        self.freq = freq
    def getFrequencies(self):
        return self.freq
    def setLog(self,log):
        self.log = log
    def getLog(self):
        return self.log
    def setEpisodes(self,episodes):
        self.episodes = episodes
    def getEpisodes(self):
        return self.episodes
    def setOccurrenceSets(self, occ):
        self.occurrence_sets = occ
    def getOccurrenceSets(self):
        return self.occurrence_sets
    
    def run(self):
        try:
            subs = self.findSubsumes()
            ret = self.handleSubsumes(subs)
        except Exception:
            import traceback
            traceback.print_exc()
            ret = []
        self.result.emit(ret)
    def stop(self):
        pass

    def build_graph(self, transitions):
        graph = {}
        predecessors = {}
        nodes = set()
        try:
            for a, b in transitions:
                graph.setdefault(a, set()).add(b)
                predecessors.setdefault(b, set()).add(a)
                nodes.add(a)
                nodes.add(b)
            for n in nodes:
                if n not in predecessors:
                    predecessors[n] = set()
            return graph, predecessors, nodes
        except Exception:
            import traceback
            traceback.print_exc()
            return {}, {}, set()

    def _transitive_closure(self, graph, nodes):
        closure = set()
        for start in nodes:
            visited = set()
            queue = list(graph.get(start, []))
            while queue:
                node = queue.pop()
                if node in visited:
                    continue
                visited.add(node)
                closure.add((start, node))
                queue.extend(graph.get(node, []))
        return closure

    def episode_to_key(self,episode_activities, episode_transitions):
        return (
            frozenset(episode_activities),
            frozenset(episode_transitions)
        )

    def build_occurrence_map(self, episode):
        activities, transitions = episode
        key = (tuple(activities), tuple(sorted(transitions)))
        occ_list = self.occurrence_sets.get(key, [])
        return {case_id: dict(zip(activities, positions)) for case_id, positions in occ_list}

    def resolveSubsume(self, ep_strict, ep_loose):
        ep_freqs = self.getFrequencies()
        strict_key = self.episode_to_key(ep_strict[0], ep_strict[1])
        loose_key = self.episode_to_key(ep_loose[0], ep_loose[1])
        freq_strict = ep_freqs.get(strict_key, 0)
        freq_loose = ep_freqs.get(loose_key, 0)
        if freq_loose > freq_strict:
            return ([ep_loose], [ep_strict], freq_strict, freq_loose)
        return ([ep_strict], [ep_loose], freq_loose, freq_strict)

    def findSubsumes(self):
        episodes = self.getEpisodes()
        toSubsume = []

        precomputed = []
        for ep in episodes:
            activities, transitions = ep
            graph, _, nodes = self.build_graph(transitions)
            closure = self._transitive_closure(graph, nodes) if nodes else set()
            precomputed.append((ep, frozenset(activities), closure))

        for i, (ep_x, acts_x, cl_x) in enumerate(precomputed):
            for j, (ep_y, acts_y, cl_y) in enumerate(precomputed):
                if i == j or episodes[i] == episodes[j]:
                    continue
                if acts_x != acts_y:
                    continue
                if cl_x == cl_y:
                    continue
                if cl_y <= cl_x:
                    toSubsume.append(self.resolveSubsume(ep_x, ep_y))

        return toSubsume
    
    def get_log_size(self,case_col="case:concept:name"):
        log=self.getLog()
        return log[case_col].nunique()
    
    def handleSubsumes(self, subsumes):
        ret = []
        def calc_tau(f_1,f_2):
            return f_1/f_2
        def calc_tau_smooth(f_1,f_2,alpha=1.0):
            f_1s = f_1 + alpha
            f_2s = f_2 + alpha
            return f_1s / f_2s
        def calc_tau_smooth_norm(f_1,f_2,logsize,alpha=0.0000000001):
            f_1s = (f_1 + alpha)/logsize
            f_2s = (f_2 + alpha)/logsize
            return f_1s / f_2s
        logsize = self.get_log_size()
        seen = set()
        for dominant, minor, freq_minor, freq_dominant in subsumes:
            for ep1 in dominant:
                ep1key = self.episode_to_key(ep1[0],ep1[1])
                for ep2 in minor:
                    ep2key = self.episode_to_key(ep2[0],ep2[1])
                    tau = calc_tau_smooth_norm(freq_minor,freq_dominant,logsize)
                    pair = (ep1key, ep2key)
                    if pair not in seen:
                        seen.add(pair)
                        ret.append(("SUBSUME",ep1,ep2,round(clamp01(tau),3)))
        return ret

class SubEpisodes(QThread):
    global CASE_COL
    log = None
    episodes = None
    freq = None
    result = pyqtSignal(object)
    def setFrequencies(self,freq):
        self.freq = freq
    def getFrequencies(self):
        return self.freq
    def setLog(self,log):
        self.log = log
    def getLog(self):
        return self.log
    def setEpisodes(self,episodes):
        self.episodes = episodes
    def getEpisodes(self):
        return self.episodes

    def run(self):
        try:
            subeps = self.findSubEpisodes()
            ret = self.handleSubEpisodes(subeps)
        except Exception:
            import traceback
            traceback.print_exc()
            ret = []
        self.result.emit(ret)
    def stop(self):
        pass
    
    def get_log_size(self,case_col="case:concept:name"):
        log=self.getLog()
        return log[case_col].nunique()
    def episode_to_key(self,episode_activities, episode_transitions):
        return (
            frozenset(episode_activities),
            frozenset(episode_transitions)
        )

    def findSubEpisodes(self):
        subEps = []
        episodes = self.getEpisodes()
        for episode in episodes:
            alphabet = episode[0]
            transitions = episode[1]
            alphabet_set = set(alphabet)
            transitions_set = set(transitions)
            for ep2 in episodes:
                if ep2 == episode:
                    continue
                isSub = True
                for ep2act in ep2[0]:
                    if ep2act not in alphabet_set:
                        isSub = False
                        break
                if not isSub:
                    continue
                for ep2trans in ep2[1]:
                    if ep2trans not in transitions_set:
                        isSub = False
                        break
                if isSub:
                    subEps.append((episode, ep2))
        return subEps
    
    def handleSubEpisodes(self, subEps):
        ep_freqs = self.getFrequencies()
        sE = []
        def calc_tau(f_1,f_2):
            return f_1/f_2
        def calc_tau_smooth(f_1,f_2,alpha=1.0):
            f_1s = f_1 + alpha
            f_2s = f_2 + alpha
            return f_1s / f_2s
        def calc_tau_smooth_norm(f_1,f_2,logsize,alpha=0.0000000001):
            f_1s = (f_1 + alpha)/logsize
            f_2s = (f_2 + alpha)/logsize
            return f_1s / f_2s

        logsize = self.get_log_size()
        seen = set()
        for comb in subEps:
            ep1 = comb[0]
            ep1key = self.episode_to_key(ep1[0],ep1[1])
            freq_ep1 = ep_freqs.get(ep1key,0)
            ep2 = comb[1]
            ep2key = self.episode_to_key(ep2[0],ep2[1])
            freq_ep2 = ep_freqs.get(ep2key,0)
            tau = calc_tau_smooth_norm(freq_ep1,freq_ep2,logsize)
            pair = (ep1key, ep2key)
            if pair not in seen:
                seen.add(pair)
                sE.append(("SUBEP",ep1,ep2,round(clamp01(tau),3)))
        return sE

class Reorder(QThread):
    log = None
    episodes = None
    freq = None
    result = pyqtSignal(object)

    def setFrequencies(self, freq):
        self.freq = freq
    def getFrequencies(self):
        return self.freq
    def setLog(self, log):
        self.log = log
    def getLog(self):
        return self.log
    def setEpisodes(self, episodes):
        self.episodes = episodes
    def getEpisodes(self):
        return self.episodes

    def run(self):
        try:
            candidates = self.findReorderCandidates()
            ret = self.handleReorderCandidates(candidates)
        except Exception:
            import traceback
            traceback.print_exc()
            ret = []
        self.result.emit(ret)

    def stop(self):
        pass

    def episode_to_key(self, episode_activities, episode_transitions):
        return (
            frozenset(episode_activities),
            frozenset(episode_transitions)
        )

    def findReorderCandidates(self):
        episodes = self.getEpisodes()
        n = len(episodes)

        prepared = []
        for ep in episodes:
            activities, transitions = ep
            prepared.append((ep, frozenset(activities), frozenset(transitions)))

        candidates = []
        for i in range(n):
            ep_i, acts_i, trans_i = prepared[i]
            for j in range(i + 1, n):
                ep_j, acts_j, trans_j = prepared[j]

                if acts_i != acts_j:
                    continue
                if trans_i == trans_j:
                    continue

                candidates.append((ep_i, ep_j))

        return candidates

    def handleReorderCandidates(self, candidates):
        ep_freqs = self.getFrequencies()
        alpha = 0.0000000001

        ret = []
        seen = set()
        for ep_a, ep_b in candidates:
            key_a = self.episode_to_key(ep_a[0], ep_a[1])
            key_b = self.episode_to_key(ep_b[0], ep_b[1])

            freq_a = ep_freqs.get(key_a, 0)
            freq_b = ep_freqs.get(key_b, 0)

            if freq_a > freq_b:
                dominant, minor = ep_a, ep_b
                freq_dominant, freq_minor = freq_a, freq_b
            elif freq_b > freq_a:
                dominant, minor = ep_b, ep_a
                freq_dominant, freq_minor = freq_b, freq_a
            else:
                if str(sorted(ep_a[1])) <= str(sorted(ep_b[1])):
                    dominant, minor = ep_a, ep_b
                else:
                    dominant, minor = ep_b, ep_a
                freq_dominant, freq_minor = freq_a, freq_b

            tau = 1 - (freq_minor + alpha) / (freq_dominant + alpha)

            dom_key = self.episode_to_key(dominant[0], dominant[1])
            min_key = self.episode_to_key(minor[0], minor[1])
            pair = (dom_key, min_key)
            if pair in seen:
                continue
            seen.add(pair)

            ret.append(("REORDER", dominant, minor, round(clamp01(tau), 3)))

        return ret

class SingleDiff(QThread):

    log = None
    episodes = None
    freq = None
    result = pyqtSignal(object)

    Struct = []
    occurrence_sets = {}

    def setFrequencies(self, freq):
        self.freq = freq

    def getFrequencies(self):
        return self.freq

    def setLog(self, log):
        self.log = log

    def getLog(self):
        return self.log

    def setEpisodes(self, episodes):
        self.episodes = episodes

    def getEpisodes(self):
        return self.episodes

    def setStruct(self, nstruct):
        self.Struct = nstruct

    def getStruct(self):
        return self.Struct

    def setOccurrenceSets(self, occ):
        self.occurrence_sets = occ

    def getOccurrenceSets(self):
        return self.occurrence_sets

    def run(self):
        try:
            ret = self.findSingleDiff()
        except Exception:
            import traceback
            print("[SingleDiff] CRASHED - emitting empty result so the "
                  "pipeline doesn't stall. Traceback:")
            traceback.print_exc()
            ret = []
        self.result.emit(ret)

    def stop(self):
        pass

    def findSingleDiff(self):
        log = self.getLog().copy()

        episode_activities = set()
        for acts, _ in (self.getEpisodes() or []):
            episode_activities.update(acts)

        struct_map = {}
        for label, activity, data in self.getStruct():
            if activity in episode_activities:
                struct_map[activity] = data
        if len(struct_map) < 2:
            return []

        activity_cases = defaultdict(set)
        for case_id, group in log.groupby("case:concept:name")["concept:name"]:
            for act in set(group):
                if act in struct_map:
                    activity_cases[act].add(case_id)

        activity_timestamps = {}
        try:
            for act in struct_map:
                ts = (
                    log.loc[log["concept:name"] == act, "time:timestamp"]
                    .sort_values()
                    .tolist()
                )
                activity_timestamps[act] = ts
        except:
            activity_timestamps = None

        def jaccard(s1, s2):
            if not s1 and not s2:
                return 1.0
            if not s1 or not s2:
                return 0.0
            return len(s1 & s2) / len(s1 | s2)

        def structural_similarity(a, b):
            a_data = struct_map[a]
            b_data = struct_map[b]
            pre  = jaccard(a_data["preset"],  b_data["preset"])
            post = jaccard(a_data["postset"], b_data["postset"])
            return 0.5 * (pre + post)

        def co_occurrence(a, b):
            s1 = activity_cases[a]
            s2 = activity_cases[b]
            if not s1 and not s2:
                return 0.0
            return len(s1 & s2) / len(s1 | s2)

        def precedence_probability(a, b):
            ts_a = activity_timestamps.get(a, [])
            ts_b = activity_timestamps.get(b, [])
            if not ts_a or not ts_b:
                return 0.0
            total = len(ts_a) * len(ts_b)
            count = sum(len(ts_b) - bisect_right(ts_b, ta) for ta in ts_a)
            return count / total

        activities = list(struct_map.keys())
        results = []

        for i in range(len(activities)):
            for j in range(i + 1, len(activities)):

                a = activities[i]
                b = activities[j]

                sim = structural_similarity(a, b)
                if sim < 0.5:
                    continue

                co = co_occurrence(a, b)

                sim_co = sim * (1 - co)

                if sim_co > 0.6 and activity_timestamps:
                    prec_ab = precedence_probability(a, b)
                    prec_ba = precedence_probability(b, a)

                    update_ab = sim_co * prec_ab
                    update_ba = sim_co * prec_ba
                    max_update = max(update_ab, update_ba)

                    if max_update > 0.6:
                        if update_ab > update_ba:
                            results.append(("UPDATE", a, b, round(clamp01(update_ab), 3)))
                        else:
                            results.append(("UPDATE", b, a, round(clamp01(update_ba), 3)))
                        continue

                if sim_co > 0.5:
                    results.append(("CHOICE", [a, b], round(clamp01(sim_co), 3)))

        return results
    
class Relater(QThread):
    occurrence_sets = {}

    def setOccurrenceSets(self, occ):
        self.occurrence_sets = occ

    def getOccurrenceSets(self):
        return self.occurrence_sets
    
    global CASE_COL
    log = None
    episodes = None
    freq = None
    toCombine = []
    toUpdate = []
    toChoice = [] 
    toSubsume = []
    related = []
    relatedACT = []
    related2 = []
    AR = []
    DR = []
    HS = []
    TAG = []
    DIS = []
    Threads = []
    fuzdep = QThread
    resultReady = pyqtSignal(object)
    progress = pyqtSignal(int, int)  # (completed_steps, total_steps)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._completed_steps = 0

    def _report_step_complete(self):
        self._completed_steps += 1
        self.progress.emit(self._completed_steps, len(self.Threads))

    def setFrequencies(self,freq):
        self.freq = freq
    def getFrequencies(self):
        return self.freq
    def setLog(self,log):
        self.log = log
    def getLog(self):
        return self.log
    def setEpisodes(self,episodes):
        self.episodes = episodes
    def getEpisodes(self):
        return self.episodes
    def handleSignal(self,value):
        self.DIS.extend(value)
        self._report_step_complete()
    def handleSignalHS(self,value):
        self.HS.extend(value)
        self._report_step_complete()
    def handleSignalDR(self,value):
        self.DR.extend(value)
        self._report_step_complete()
    def handleSignalAR(self,value):
        self.AR.extend(value)
        self._report_step_complete()
    def handleSignalTAG(self,value):
        self.TAG.extend(value)
        self.SiDiff.setStruct(self.TAG)
        self.SiDiff.start()
        self._report_step_complete()
    def handleSignalAbsCon(self,value):
        self.DR.extend(value)
        self._report_step_complete()

    #Signal connections
    probDep = ProbabilisticDependency()
    structured = Structuredness()
    AbsCon = AbsoluteConnection()
    AbsEx = AbsoluteExclusion()
    SubSu = Subsume()
    SubEpi = SubEpisodes()
    Reord = Reorder()
    SiDiff = SingleDiff()
    Threads.append(probDep)
    Threads.append(structured)
    Threads.append(AbsCon)
    Threads.append(AbsEx)
    Threads.append(SubSu)
    Threads.append(SubEpi)
    Threads.append(Reord)
    Threads.append(SiDiff)

    def run(self):
        self.probDep.result.connect(self.handleSignalDR)
        self.structured.result.connect(self.handleSignalTAG)
        self.AbsCon.result.connect(self.handleSignalAbsCon)
        self.AbsEx.result.connect(self.handleSignalDR)
        self.SubSu.result.connect(self.handleSignalHS)
        self.SubEpi.result.connect(self.handleSignalHS)
        self.Reord.result.connect(self.handleSignalHS)
        self.SiDiff.result.connect(self.handleSignalAR)

        logdf = self.getLog()
        eps = self.getEpisodes()
        self.setFrequencies(self.count_episode_frequencies())
        self.probDep.setLog(logdf)
        self.probDep.setEpisodes(eps)
        self.probDep.setFrequencies(self.getFrequencies())
        self.structured.setLog(logdf)
        self.structured.setEpisodes(eps)
        self.structured.setFrequencies(self.getFrequencies())
        self.AbsCon.setLog(logdf)
        self.AbsCon.setEpisodes(eps)
        self.AbsCon.setFrequencies(self.getFrequencies())
        self.AbsEx.setLog(logdf)
        self.AbsEx.setEpisodes(eps)
        self.AbsEx.setFrequencies(self.getFrequencies())
        self.SubSu.setLog(logdf)
        self.SubSu.setEpisodes(eps)
        self.SubSu.setFrequencies(self.getFrequencies())
        self.SubEpi.setLog(logdf)
        self.SubEpi.setEpisodes(eps)
        self.SubEpi.setFrequencies(self.getFrequencies())
        self.Reord.setLog(logdf)
        self.Reord.setEpisodes(eps)
        self.Reord.setFrequencies(self.getFrequencies())
        self.SiDiff.setLog(logdf)
        self.SiDiff.setEpisodes(eps)
        self.SiDiff.setFrequencies(self.getFrequencies())
        self.probDep.setOccurrenceSets(self.getOccurrenceSets())
        self.AbsCon.setOccurrenceSets(self.getOccurrenceSets())
        self.AbsEx.setOccurrenceSets(self.getOccurrenceSets())
        self.SiDiff.setOccurrenceSets(self.getOccurrenceSets())
        self.SubSu.setOccurrenceSets(self.getOccurrenceSets())

        self.probDep.start()
        self.structured.start()
        self.AbsCon.start()
        self.AbsEx.start()
        self.SubSu.start()
        self.SubEpi.start()
        self.Reord.start()
        for t in self.Threads:
            t.wait()
        self.resultReady.emit((self.AR,self.DR,self.TAG,self.HS))
    def stop(self):
        pass
    
    def get_log_size(self,case_col="case:concept:name"):
        log=self.getLog()
        return log[case_col].nunique()
    
    def count_episode_frequencies(self):
        episodes = self.getEpisodes()
        occurrence_sets = self.getOccurrenceSets()

        episode_frequencies = {}
        for episode_activities, episode_transitions in episodes:
            occ_key = (tuple(episode_activities), tuple(sorted(episode_transitions)))
            occ_set = occurrence_sets.get(occ_key, [])

            freq_key = (
                frozenset(episode_activities),
                frozenset(episode_transitions)
            )
            episode_frequencies[freq_key] = len(occ_set)

        return episode_frequencies

class InputWindow(QWidget):
    start = pyqtSignal()
    def __init__(self):
        super().__init__()
        self.theme = detect_theme()
        self.setStyleSheet(build_stylesheet(self.theme))
        self.initUI()
    
    def msg_wait(self, s):
        msg = QMessageBox()
        msg.setText(s)
        msg.setWindowTitle(" ")
        msg.setModal(False)
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        
        msg.show()
        return msg

    def chooseFileLog(self,button):
        FS = QFileDialog(self)
        input_file = FS.getOpenFileName(None, 'Open File', "" ,self.tr("XES Event Log (*.xes *.xes.gz)"))
        try:
            file_ex1 = input_file[0].split(".")[-1]
            file_ex2 = input_file[0].split(".")[-2]
        except:
            return
        if(not file_ex1=="xes" and not (file_ex2=="xes" and file_ex1=="gz")):
           self.msg_wait("Please select a valid file")
           return self.chooseFileLog(button)
        if(input_file!=('', '')):
            button.setText(input_file[0])

    def chooseFileEPS(self,button):
        FS = QFileDialog(self)
        input_file = FS.getOpenFileName(None, 'Open File', "" ,self.tr("Episode File (*.txt)"))
        try:
            file_ex1 = input_file[0].split(".")[-1]
        except:
            return
        if(not file_ex1 =="txt" ):
           self.msg_wait("Please select a valids file")
           return self.chooseFileEPS(button)
        if(input_file!=('', '')):
            button.setText(input_file[0])

    def set_progress_indeterminate(self, status_text):
        self.progress_bar.setRange(0, 0)
        self.progress_status.setText(status_text)

    def set_progress_value(self, completed, total, status_text=None):
        self.progress_bar.setRange(0, max(total, 1))
        self.progress_bar.setValue(completed)
        if status_text is not None:
            self.progress_status.setText(status_text)
        else:
            self.progress_status.setText(f"Analyzing relations… ({completed}/{total})")

    def show_progress(self):
        self.progress_bar.show()
        self.progress_status.show()
        self.LOGFS.setEnabled(False)
        self.EPFS.setEnabled(False)
        self.start_button.setEnabled(False)

    def initUI(self):
        def startProcess():
            global EPSFILE
            global XES_LOCATION
            global EPS
            EPS = []
            if self.LOGFS.text() == "Select Log File" or self.EPFS.text() == "Select Episode File":
                self.msg_wait("Please select a valid Event Log and a List of Episodes")
            else:
                EPSFILE = self.EPFS.text()
                XES_LOCATION = self.LOGFS.text()
                self.show_progress()
                self.set_progress_indeterminate("Loading event log and episodes…")
                self.start.emit()

        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(28, 26, 28, 26)
        outer_layout.setSpacing(14)

        self.setWindowTitle("Select Log and Episode Input")
        self.setGeometry(100, 100, 420, 200)

        title = QLabel("Load Event Log & Episodes")
        title.setObjectName("panelTitle")
        outer_layout.addWidget(title)

        subtitle = QLabel("Select an XES event log and an episode definition file to begin.")
        subtitle.setWordWrap(True)
        outer_layout.addWidget(subtitle)

        formlayout = QFormLayout()
        formlayout.setVerticalSpacing(10)

        self.LOGFS = QPushButton("Select Log File")
        self.LOGFS.setMinimumHeight(34)
        self.LOGFS.clicked.connect(lambda: self.chooseFileLog(self.LOGFS))
        formlayout.addRow(self.LOGFS)
        self.EPFS = QPushButton("Select Episode File")
        self.EPFS.setMinimumHeight(34)
        self.EPFS.clicked.connect(lambda: self.chooseFileEPS(self.EPFS))
        formlayout.addRow(self.EPFS)

        outer_layout.addLayout(formlayout)
        outer_layout.addSpacing(6)

        self.start_button = QPushButton("Start Process")
        self.start_button.setObjectName("primaryButton")
        self.start_button.setMinimumHeight(36)
        self.start_button.clicked.connect(startProcess)
        outer_layout.addWidget(self.start_button)

        self.progress_status = QLabel("")
        self.progress_status.setWordWrap(True)
        self.progress_status.hide()
        outer_layout.addWidget(self.progress_status)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimumHeight(16)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.hide()
        outer_layout.addWidget(self.progress_bar)

        self.setLayout(outer_layout)
        
def preProcessEPS(episodes, log_df):

    def has_alternative_path(graph, start, end, ignore_edge):
        q = deque([start])
        visited = {start}

        while q:
            node = q.popleft()
            for nxt in graph[node]:
                if (node, nxt) == ignore_edge:
                    continue
                if nxt == end:
                    return True
                if nxt not in visited:
                    visited.add(nxt)
                    q.append(nxt)
        return False

    def transitive_reduction_edges(activities, transitions):
        graph = defaultdict(list)
        for a, b in transitions:
            graph[a].append(b)

        reduced = set(transitions)

        for u, v in transitions:
            if has_alternative_path(graph, u, v, (u, v)):
                reduced.discard((u, v))

        return tuple(sorted(reduced))

    def episode_in_trace(trace, episode):
        activities, transitions = episode

        activities = list(activities)
        activity_set = set(activities)

        window_size = len(activities) + 1
        n = len(trace)
        effective_window_size = min(window_size, n)

        for start in range(0, n - effective_window_size + 1):
            window = trace[start:start + effective_window_size]
            positions = {
                act: [i for i, x in enumerate(window) if x == act]
                for act in activity_set
            }

            if any(len(pos_list) == 0 for pos_list in positions.values()):
                continue

            candidate_lists = [positions[a] for a in activities]

            for candidate in product(*candidate_lists):
                assignment = dict(zip(activities, candidate))
                valid = True
                for a, b in transitions:
                    if assignment[a] >= assignment[b]:
                        valid = False
                        break

                if valid:
                    return [start + assignment[a] for a in activities]

        return None

    traces = (
        log_df.sort_index()
        .groupby(CASE_COL)[ACTIVITY_COL]
        .apply(list)
        .to_dict()
    )

    episode_keys = {
        tuple(sorted(transitions))
        for _, transitions in episodes
    }

    filtered = []
    occurrence_sets = {}

    for activities, transitions in episodes:
        reduced = transitive_reduction_edges(activities, transitions)

        if reduced != tuple(sorted(transitions)) and reduced in episode_keys:
            continue

        ep = (activities, transitions)

        occ = []
        for case_id, trace in traces.items():
            positions = episode_in_trace(trace, ep)
            if positions is not None:
                occ.append((case_id, positions))

        filtered.append(ep)
        occurrence_sets[(tuple(activities), tuple(sorted(transitions)))] = occ

    return filtered, occurrence_sets

def compute_episode_frequencies(occurrence_sets, total_traces, normalize=False):
    frequencies = {}

    for ep_key, occ_set in occurrence_sets.items():
        count = len(occ_set)
        if normalize:
            frequencies[ep_key] = count / total_traces
        else:
            frequencies[ep_key] = count

    return frequencies

def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(build_stylesheet(detect_theme()))
    rel = Relater()
    def startRelater():
        global XES_LOCATION
        global EPS
        global EPSFILE
        inputwindow.set_progress_indeterminate("Reading episode definitions…")
        app.processEvents()
        if not EPS:
            if not EPSFILE:
                print("No episodes FOUND")
                EPS = []
            else:
                con = Converter(EPSFILE)
                EPS = con.run()
        
        viz = EpisodeVisualizer()
        def updateViz(value):
            inputwindow.set_progress_value(len(rel.Threads), len(rel.Threads), "Building visualization…")
            app.processEvents()
            viz.episodes = EPS
            viz.actUPChoice = value[0]
            viz.directRelations = value[1]
            viz.tagRelations = value[2]
            viz.showHideRelations = value[3]
            viz.set_episode_occurrences(freq_set)
            viz.set_occurrence_sets(occ_sets)
            viz.set_total_traces(logdf["case:concept:name"].nunique())
            viz.min_episode_scale = 0.8
            viz.max_episode_scale = 1.5
            viz.build_visualization()
            viz.show()
            inputwindow.hide()

        def onRelaterProgress(completed, total):
            inputwindow.set_progress_value(completed, total)

        rel.resultReady.connect(updateViz)
        rel.progress.connect(onRelaterProgress)

        inputwindow.set_progress_indeterminate("Loading event log…")
        app.processEvents()
        logdf = convertLogToDf(XES_LOCATION)

        inputwindow.set_progress_indeterminate("Preparing episodes…")
        app.processEvents()
        EPS, occ_sets = preProcessEPS(EPS, logdf)
        total_traces = logdf[CASE_COL].nunique()
        freq_set = compute_episode_frequencies(occ_sets,total_traces,normalize=True)

        rel.setLog(logdf)
        rel.setEpisodes(EPS)
        rel.setOccurrenceSets(occ_sets)

        inputwindow.set_progress_value(0, len(rel.Threads), "Analyzing relations…")
        rel.start()
    inputwindow = InputWindow()
    inputwindow.start.connect(startRelater)
    inputwindow.show()
    sys.exit(app.exec())

def convertLogToDf(xes_path):
    return pm4py.read_xes(xes_path)

if __name__ == '__main__':
     main()
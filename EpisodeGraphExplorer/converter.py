import re
from PyQt6.QtCore import QThread

class Converter(QThread):
    def __init__(self,epfile):
        self.epfile = epfile
    def run(self):
        episodes = self.parse_file(self.epfile)
        return episodes

    def parse_episode_line(self,line):
        line = line.strip()[2:-1]
        transition_matches = re.findall(r'\((\d+)\s*->\s*(\d+)\)', line)
        transitions = [(int(i), int(j)) for i, j in transition_matches]
        line_without_transitions = re.sub(r'\(\d+\s*->\s*\d+\)', '', line)
        events = [e.strip() for e in line_without_transitions.split(',') if e.strip()]
        mapped_transitions = [(events[i], events[j]) for i, j in transitions]
        return (events, mapped_transitions)


    def parse_file(self,filename):
        episodes = []
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('E['):
                    episodes.append(self.parse_episode_line(line))
        return episodes

if __name__ == "__main__":
    filename = ""
    con = Converter(filename)
    con.run()
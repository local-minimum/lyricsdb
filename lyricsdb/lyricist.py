from collections import defaultdict
from random import randrange
from .text import reverse_graph, get_morphmeme_dict, get_alliteration_lexicon, get_rhyme_lexicon, make_string


class Lyricist(object):

    def __init__(self, word_graph, morphemes):

        # Word graph
        self._forward_graph = word_graph
        self._reverse_graph = reverse_graph(word_graph)

        # Morphemes
        self._morphemes = morphemes

        # Settings for evaluating alliterations, requires morphemes
        self._alliteration_settings = defaultdict(int)
        self._alliteration_lexicon = None

        # Settings for rhyming, requires morphemes.
        self._rhyme_settings = defaultdict(int)
        self._rhyme_lexicon = None
        self._rhyme_memory = defaultdict(int)

        # Promote consistent phraseology
        self._phrasing_settings = defaultdict(int)

        # Words with few edges in and out could be good to repeat
        self._theme_settings = defaultdict(int)
        self._themed_words = defaultdict(int)

        self._text = []

        self._line_endings = (None, '.', '?', "!", ":", "-")
        self._phrase_endings = (',', ';')

    def set_rhyme_lexicon(self, lex):

        self._rhyme_lexicon = lex

    def set_rhyme_settings(self, auto=None, repeat=None, rhymability=None, cap=None):

        if auto is not None:
            self._rhyme_settings['auto-rhymining'] = auto

        if repeat is not None:
            self._rhyme_settings['repeat'] = repeat

        if rhymability is not None:
            self._rhyme_settings['rhymability'] = rhymability

        if cap is not None:

            if cap == -1:
                self._rhyme_settings['cap'] = None
            else:
                self._rhyme_settings['cap'] = cap

    def set_alliteration_lexicon(self, lex):

        self._alliteration_lexicon = lex

    def compose(self, lines=10):

        entries = self._forward_graph[None].keys()
        node = entries[randrange(0, len(entries))]
        max_line_words = 10
        line_words = 0
        while lines > 0:

            edges = self.evaluate(node)
            total = sum(edges.values())

            if total == 0:

                print("** No valid edge for {0} (base-edges: {1})".format(node, self._forward_graph[node]))
                self.update(node, None)
                lines -= 1
                line_words = 0
                node = None

            else:

                choice = randrange(0, total)
                for edge, weight in edges.iteritems():

                    if choice < weight:

                        self.update(node, edge)
                        node = edge

                        if edge in self._line_endings:
                            lines -= 1
                            line_words = 0
                        else:
                            line_words += 1
                        break

                    else:
                        choice -= weight

            if max_line_words == line_words:
                line_words = 0
                self.update(node, None)
                lines -= 1

        return self

    def evaluate(self, word):
        """Recalculate weights

        :param word: the current node
        :return: Recalculated weights fro the words
        """
        stats = {edge: count for edge, count in self._forward_graph[word].iteritems()}

        if self._rhyme_lexicon:
            stats = {edge: count + self._get_rhyme_value(edge) for edge, count in stats.iteritems()}

        if self._alliteration_lexicon:
            stats = {edge: count + self._get_alliteration_value(edge) for edge, count in stats.iteritems()}

        return stats

    def _get_rhyme_value(self, word):

        rhyme = self._morphemes[word][-1]

        bonus = 0
        if rhyme in self._rhyme_lexicon:
            if word in self._rhyme_memory:
                bonus = self._rhyme_settings['auto-rhyming']
            else:
                bonus = len(self._rhyme_lexicon[rhyme]) * self._rhyme_settings['rhymability'] + \
                       self._rhyme_memory[rhyme] * self._rhyme_settings['repeat']
        elif rhyme in self._rhyme_memory:
            bonus = self._rhyme_settings['auto-rhyming']

        if self._rhyme_settings['cap'] is None:
            return bonus
        else:
            return min(bonus, self._rhyme_settings['cap'])

    def _get_alliteration_value(self, word):

        return 0

    def update(self, word, next_word):
        """Let lyricist know which you selected

        :param word:
        :param next_word:
        """

        if self._text:
            self._text.append(next_word)
            if next_word in self._line_endings and next_word is not None:
                self._text.append(None)
        else:
            self._text.append(next_word.capitalize())

        if next_word in self._line_endings or next_word in self._phrase_endings:

            rhyme = self._morphemes[word][-1]
            if rhyme != word:
                self._rhyme_memory[word] += 1
            self._rhyme_memory[rhyme] += 1

    @property
    def song(self):

        prev = 0

        for cur, w in enumerate(self._text):

            if w is None:
                yield make_string(self._text[prev: cur])
                prev = cur + 1

    @property
    def song_as_string(self):

        return "\n".join(self.song)


def hiphoper(word_graph):

    morphemes = get_morphmeme_dict(word_graph)
    poet = Lyricist(word_graph, morphemes)
    poet.set_rhyme_settings(cap=-1, auto=1, repeat=1, rhymability=1)
    poet.set_rhyme_lexicon(get_rhyme_lexicon(morphemes))

    return poet

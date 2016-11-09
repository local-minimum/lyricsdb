import re
from collections import defaultdict
from random import randint
from csv import writer, reader
from itertools import izip


word_tokenizer = re.compile(r"[\w\-']+|[,:;\.!\?\"]")


def text_to_words(songs):

    global word_tokenizer

    return [[word_tokenizer.findall(line) for line in song] for song in songs if song is not None]


def word_counter(words):

    counts = defaultdict(int)
    for song in words:
        for line in song:
            for word in line:
                counts[word] += 1

    return counts


def top_words(counts, n=20):
    return sorted(counts.iteritems(), key=lambda v: v[1], reverse=True)[:n]


def count_bigrams(words, per_line=False):

    counts = defaultdict(int)

    for song in words:

        previous = None

        for line in song:

            if per_line:
                previous = None

            for word in line:

                counts[(previous, word)] += 1

                previous = word

            if per_line:

                counts[(previous, None)] += 1

        counts[(previous, None)] += 1

    return counts


def graph_bigrams(bigram_count):

    graph = defaultdict(lambda: defaultdict(int))

    for (node, edge), counts in bigram_count.iteritems():

        graph[node][edge] = counts

    return graph


def reverse_graph(word_graph):

    graph = defaultdict(lambda: defaultdict(int))

    for node in word_graph:

        for edge in word_graph[node]:

            graph[edge][node] += word_graph[node][edge]

    return graph


def get_sentence(bigram_graph, previous=None, max_words=15, end_at=(u".",)):

    sentence = []

    while len(sentence) < max_words:

        counts = sum(bigram_graph[previous].values())
        if counts == 0:
            break

        rnd = randint(0, counts)

        for edge, edge_count in bigram_graph[previous].iteritems():

            if rnd < edge_count:

                if edge is None:
                    return sentence, edge

                sentence.append(edge)
                previous = edge
                break

            else:

                rnd -= edge_count

            if previous in end_at:
                return sentence, sentence[-1]

    return sentence, sentence[-1]


def make_string(sentence):

    return re.sub(r' ([,.:;!?])', r'\1', u' '.join(sentence))


def make_song(graph, lines=20, previous=None, **kwargs):

    for _ in range(lines):

        line, previous = get_sentence(graph, previous, **kwargs)
        yield make_string(line)


def dump_graph(graph, target):

    with open(target, 'wb') as fh:

        w = writer(fh)

        for node, edges in graph.iteritems():

            node = u'' if node is None else node

            for edge, count in edges.iteritems():

                w.writerow((node, u'' if edge is None else edge, count))


def load_graph(source):

    graph = defaultdict(lambda: defaultdict(int))
    with open(source, 'rb') as fh:

        r = reader(fh)

        for node, edge, count in r:

            graph[node if node else None][edge if edge else None] = int(count)

    return graph

WOVELS = "aeiouyAEIOUY"
CONSONANTS_PLUS = "QqWwRrTtPp'SsDdFfGgHhJjKkLlZzXxCcVvBbNnMm"


def categorize_letters(word):

    for l in word:

        if l in WOVELS:
            yield 1
        elif l in CONSONANTS_PLUS:
            yield 0
        else:
            yield -1

GLUTENATED_CONSONANTS = defaultdict(bool)
GLUTENATED_CONSONANTS[('s', 't')] = True
GLUTENATED_CONSONANTS[('t', 'r')] = True
GLUTENATED_CONSONANTS[('c', 'h')] = True
GLUTENATED_CONSONANTS[('s', 'h')] = True
GLUTENATED_CONSONANTS[('s', 'c')] = True
GLUTENATED_CONSONANTS[('c', 'r')] = True
GLUTENATED_CONSONANTS[('n', 'g')] = True
GLUTENATED_CONSONANTS[('r', 'd')] = True
GLUTENATED_CONSONANTS[('p', 'h')] = True
GLUTENATED_CONSONANTS[('t', 'h')] = True


def get_proto_morphemes(word):

    if word is None:

        yield tuple()

    else:

        morpheme_start = 0
        morpheme_state = 0
        prev_char = None
        last_state_change = -1
        prev_state = -1

        for i, (val, cur_char) in enumerate(izip(categorize_letters(word), word)):

            # yield val, cur_char, morpheme_state
            if val < 0 and i != morpheme_start:

                yield word[morpheme_start: i]
                morpheme_start = i + 1
                morpheme_state = 0
            elif cur_char == prev_char or GLUTENATED_CONSONANTS[(prev_char, cur_char)]:
                pass
            elif val == 1 and morpheme_state < 1:
                morpheme_state = 1
            elif morpheme_state > 0 and val == 0:
                morpheme_state += 1
            elif morpheme_state > 1:
                yield word[morpheme_start: last_state_change]
                morpheme_start = last_state_change
                morpheme_state = 1

            prev_char = cur_char
            if prev_state != morpheme_state:
                last_state_change = i
            prev_state = morpheme_state

        if morpheme_start < len(word):
            yield word[morpheme_start:]


def get_morphemes(word):

    proto = list(get_proto_morphemes(word))
    if len(proto) > 1:
        last = proto[-1]
        for suffix in ('ing', 'es', "in'"):

            if last.endswith(suffix):
                l = len(suffix)
                proto[-2] += proto[-1][:-l]
                proto[-1] = proto[-1][-l:]

        if proto[-1][-1] not in WOVELS and proto[-2][-1] in WOVELS:

            try:
                v = [l in WOVELS for l in proto[-1]].index(True)

                proto[-2] += proto[-1][:v]
                proto[-1] = proto[-1][v:]

            except ValueError:
                pass

    return proto


def get_morphmeme_dict(graph):

    morpheme_dict = {}

    for node in graph:
        if node not in morpheme_dict:
            morpheme_dict[node] = get_morphemes(node)
        for edge in graph[node]:
            if edge not in morpheme_dict:
                morpheme_dict[edge] = get_morphemes(edge)

    return morpheme_dict


def remove_singles_in_lex(lex):
    for word in lex.keys():
        if len(set(w.lower() for w in lex[word])) == 1:
            del lex[word]


def get_rhyme_lexicon(morpheme_dict, remove_singles=True):

    lex = defaultdict(list)

    for word, morphemes in morpheme_dict.iteritems():

        if not morphemes:
            continue

        try:
            lex[morphemes[-1].lower()].append(word)
        except AttributeError:
            pass

    if remove_singles:
        remove_singles_in_lex(lex)
    return lex


def get_alliteration_lexicon(morpheme_dict, remove_singles=True):

    lex = defaultdict(list)

    for word, morphemes in morpheme_dict.iteritems():

        if not morphemes:
            continue

        try:
            lex[morphemes[0].lower()].append(word)
        except AttributeError:
            pass

    if remove_singles:
        remove_singles_in_lex(lex)

    return lex

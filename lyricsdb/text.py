import re
from collections import defaultdict
from random import randint
from csv import writer

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

    graph = defaultdict(lambda : defaultdict(int))

    for (node, edge), counts in bigram_count.iteritems():

        graph[node][edge] = counts

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
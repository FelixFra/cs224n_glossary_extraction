from subprocess import call
from nltk.tokenize import sent_tokenize, word_tokenize
import json
import re
import os
import time
#import pandas as pd
from bs4 import BeautifulSoup

def match_pattern(elem, pattern):
    re_pattern = re.compile(pattern[1])
    if pattern[0] == 'text':
        return re_pattern.match(elem.text)
    else:
        return re_pattern.match(elem.attrs[pattern[0]])

def get_text_between_elements(spans, start_pattern, end_pattern, text_pattern, definiendum_pattern):
    text = []
    between = False
    for span in spans:
        if between:
            if match_pattern(span, end_pattern):
                between = False
            else:
                if match_pattern(span, definiendum_pattern):
                    text.append("<" + span.text.strip() + "/>")
                elif match_pattern(span, text_pattern):
                    text.append(span.text)
        else:
            if match_pattern(span, start_pattern):
                between = True
                
    return text

def extract_sentences(soup, pattern_info):

    # extract chapter text
    spans = soup.find_all('span')
    text = get_text_between_elements(spans,
                                     pattern_info['chapter_start_pattern'],
                                     pattern_info['chapter_end_pattern'],
                                     pattern_info['chapter_text_pattern'],
                                     pattern_info['definiendum_pattern'])

    text = ' '.join(text)
    text = text.replace('\n', ' ')

    # remove empty parens (missing figure references usually)
    text = re.sub('\(\s*\)', '', text)

    # fix multi-line spanning words
    text = re.sub('-\s+', '', text)

    # split sentences, remove short < 3 words    
    sentences = sent_tokenize(text)
    sentences = [sent for sent in sentences if len(word_tokenize(sent)) > 3]
    sentences = [sent for sent in sentences if len(word_tokenize(sent)) < 50]

    return sentences

def merge_keyterm_in_list(x):
    terms = x
    pattern0 = re.compile('\(')
    pattern1 = re.compile('.*\(')
    pattern2 = re.compile('.*\)')
    sindexs = []
    eindexs = []
    for i,term in enumerate(terms):
        if pattern0.match(term):
            sindexs.append(i-1)
        elif pattern1.match(term):
            sindexs.append(i)
        if (pattern2.match(term)):
            eindexs.append(i+1)
    if (len(sindexs) != len(eindexs)):
        print ("WARNING: You should look into this. No matching closing found found for all key terms. Got terms as:")
        print ("%s" %(terms))

    ssize = 0
    for s,e in zip(sindexs,eindexs):
        s = s-ssize
        e = e-ssize
        terms[s:e] = [' '.join(terms[s:e])]
        ssize += e-s-1

    return terms


def extract_def_sentences_and_key_terms (sentences, textbook_info):
    
    # extract definition/non-definition sentences
    # return (def_sentences, nondef_sentences, key_terms)
    
    def_sentences = []
    nondef_sentences = []
    key_terms = []

    ipattern = re.compile(textbook_info['definiendum_include_pattern'])
    epattern = re.compile(textbook_info['definiendum_exclude_pattern'])
    for sent in sentences:
        #print (sent)
        # skip non-informative lines
        if re.match("^\W+$", sent):
            continue
        
        ## ???fixme??
        if re.match(".*(video|animation).*", sent) or \
                re.match(".*(See how).*", sent) or \
                re.match(".*(Review the characteristics).*", sent) or \
                re.match(".*https://.*", sent) or \
                re.match(".*http://.*", sent):
            continue

        m0 = merge_keyterm_in_list(ipattern.findall(sent))
        m1 = merge_keyterm_in_list(epattern.findall(sent))
        m = list(set(m0) - set(m1))
        #print (m0, m1, m)
        sent = sent.replace("<", "").replace("/>", "")
        if len(m) > 0:
            def_sentences.append(sent)
            key_terms.extend(m)
        else:
            nondef_sentences.append(sent)
    return (def_sentences, nondef_sentences, key_terms)

if __name__ == "__main__":
    
    input_dir = '../data/textbooks_html'
    output_dir = '../data/textbooks_extracted_def'

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with open("textbook_info.json") as f:
        textbook_info = json.load(f)
    textbooks = list(textbook_info.keys())

    for textbook in textbooks:
        #textbook = 'open_stax_biology_2e'
        #textbook = 'open_stax_anatomy_physiology'
        #textbook = 'open_stax_astronomy'
        #textbook = 'open_stax_chemistry_2e'
        #textbook = 'open_stax_university_physics_v1'
        #textbook = 'open_stax_university_physics_v2'
        #textbook = 'open_stax_university_physics_v3'
        #textbook = 'life_biology'
        #textbook = 'open_stax_microbiology'
        print ("Processing Textbook: {}".format(textbook))
        with open('%s/%s.html' %(input_dir, textbook), 'r') as fin:
            soup = BeautifulSoup(fin, 'lxml')
            
        # extract and write chapter sentences with defm markers
        print('Extracting Sentences with defm markers')
        sentences = extract_sentences(soup, textbook_info[textbook])

        # extract definition/non-definition sentences
        xxx = extract_def_sentences_and_key_terms(sentences, 
                                                  textbook_info[textbook])
        def_sentences, nondef_sentences, key_terms = xxx

        # write out def/nodef sentences
        fname = '%s/%s_def.txt' %(output_dir, textbook)
        print ("Writing {}".format(fname))
        with open(fname, 'w') as fout:
            for sentence in def_sentences:
                fout.write('%s\n' % sentence)

        fname = '%s/%s_nondef.txt' %(output_dir, textbook)
        print ("Writing {}".format(fname))
        with open(fname, 'w') as fout:
            for sentence in nondef_sentences:
                fout.write('%s\n' % sentence)

        fname = '%s/%s_key_terms.txt' %(output_dir, textbook)
        print ("Writing {}".format(fname))
        with open(fname, 'w') as fout:
            for term in key_terms:
                fout.write('%s\n' % term)
        

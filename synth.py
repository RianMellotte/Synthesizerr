##!/usr/bin/env python3

import os
import simpleaudio
import argparse
from nltk.util import Index
from nltk.corpus.reader.util import *
from nltk.corpus.reader.api import *
import re
import nltk
import nltk.tokenize
import numpy as np

### NOTE: DO NOT CHANGE ANY OF THE EXISTING ARGUMENTS
# parser = argparse.ArgumentParser(
#     description='A basic text-to-speech app that synthesises an input phrase using diphone unit selection.')
# # parser.add_argument('--diphones', default="./diphones", help="Folder containing diphone wavs")
# parser.add_argument('--play', '-p', action="store_true", default=False, help="Play the output audio")
# parser.add_argument('--outfile', '-o', action="store", dest="outfile", type=str, help="Save the output audio to a file",
#                     default=None)
# parser.add_argument('--phrase', nargs=1, help="The phrase to be synthesised")
#
# # Arguments for extensions
# parser.add_argument('--spell', '-s', action="store_true", default=False,
#                    help="Spell the phrase instead of pronouncing it")
# #parser.add_argument('--reverse', '-r', action="store_true", default=False,
# #                    help="Speak backwards")
# parser.add_argument('--crossfade', '-c', action="store_true", default=False,
# 					help="Enable slightly smoother concatenation by cross-fading between diphone units")
# parser.add_argument('--volume', '-v', default=None, type=int,
#                     help="An int between 0 and 100 representing the desired volume")
#
# args = parser.parse_args()

class Synth:
    def __init__(self, wav_folder="./diphones"):
        # initialize Synth by creating a dictionary of the diphone wav files in the wav_folder
        self.diphones = {}
        self.out = simpleaudio.Audio()
        self.get_wavs(wav_folder)

    def get_wavs(self, wav_folder):
        #create dictionary with diphones as keys and corresponding file names in wav_folder as values
        for root, dirs, files in os.walk(wav_folder, topdown=False):
            for file in files:
                self.diphones[re.sub(r'\.wav', '', file).upper()] = '{}/{}'.format(wav_folder, file)
        # set up parameters of self.out audio based on the input diphones' audio settings
        self.out.load(list(self.diphones.values())[0])

    def create_synthesis(self, diphone_seq):
        # synthesize the input diphone sequence and save the synthesis to self.out
        milliseconds = int(self.out.rate * 0.001)
        # if crossfade command is not given, arrays are overlapped by 1 frame
        # if args.crossfade is False:
        #     # np.append could have been used to not overlap the arrays at all, but it
        #     # was more code efficient to use the crossfade method
        #     self.out.data = np.zeros(1)
        #     self.crossfade_diphones(diphone_seq, 1)
        # # if crossfade command is given, arrays are overlapped by 10 milliseconds of frames
        # else:
        self.out.data = np.zeros(10*milliseconds)
        self.crossfade_diphones(diphone_seq, 10*milliseconds)
        # round array to give correct output
        self.out.data = np.rint(self.out.data).astype(self.out.nptype)

    def crossfade_diphones(self, diphone_seq, crossover):
        # function to crossfade a diphone sequence, over a specified number of points(crossover value)
        milliseconds = int(self.out.rate * 0.001)
        # create long and short pause
        longpause = simpleaudio.Audio()
        longpause.create_tone(0, 400 * milliseconds, 1)
        shortpause = simpleaudio.Audio()
        shortpause.create_tone(0, 200 * milliseconds, 1)
        for diphone in diphone_seq:
            # for each diphone in the sequence
            try:
                # try to load the corresponding diphone file from wav_folder
                diphone_audio = simpleaudio.Audio()
                diphone_audio.load(self.diphones[diphone])
                # and then crossfade the obtained audio array into the self.out audio data
                self.crossfade_arrays(diphone_audio, crossover)
            except KeyError:
                # if the diphone is not in the wav_folder, check if it is valid punctuation
                # and crossfade in the relevant length of silence
                try:
                  if diphone in ['!', '?', ':', '.']:
                    self.crossfade_arrays(longpause, crossover)
                  elif diphone in [',']:
                    self.crossfade_arrays(shortpause, crossover)
                  else:
                      raise KeyError
                # if the diphone is not in the wav_folder or valid punctuation, user is alerted
                except KeyError:
                    print('Sorry, I am unable to retrieve the audio for the diphone {}. Please recheck that it'
                          'is in the diphones folder supplied.'.format(diphone))


    def crossfade_arrays(self, input_array, crossover):
        # take an input_array and crossfade the audio data onto the end of the self.out audio data, over the crossover period
        # array for evenly scaling amplitude of input_array up and down from 0 to 1 over crossover period
        array = np.arange(1, (crossover) + 1).astype(self.out.nptype)
        array = array / crossover
        # scale the input_array's amplitude at the start and end of the array
        np.multiply(np.flip(array), input_array.data[-crossover:],
                    out=np.rint(input_array.data[-crossover:]))
        np.multiply(array, input_array.data[:crossover],
                    out=np.rint(input_array.data[:crossover]))
        # lengthen the self.out audio array by the necessary amount and then add the input_array
        self.out.data = np.append(self.out.data, np.zeros(int(input_array.data.shape[0] - crossover)))
        self.out.data[int(-input_array.data.shape[0]):] += input_array.data


class Utterance:
    def __init__(self, phrase: object) -> object:
        # normalize input phrase to turn dates and numbers to words and remove most punctuation
        self.phrase = self.datetostring(phrase)
        self.phrase = self.digit2string(self.phrase)
        self.phrase = re.sub(r'[^A-Za-z\s\'.:!?,]+', '', self.phrase).lower()
        # get phone and diphone sequence from phrase
        self.get_phone_seq()
        self.get_diphone_seq()
        # check to make sure there is still something left in self.phrase to synthesise
        if self.phrase == '':
            print('Sorry, I couldn\'t synthesize any of that input. Please try again.')
            exit()


    def get_diphone_seq(self):
        # use the phone sequence for the phrase to create the diphone sequence
        # create list to populate with diphones
        self.diphone_seq = []
        # for each phone in the phone sequence:
        for phone_number in range(0, len(self.phone_seq) - 1):
            # if the phone is valid punctuation, then append it to the diphones sequence
            if re.match(r'[?!:.,]', self.phone_seq[phone_number]):
                self.diphone_seq.append(self.phone_seq[phone_number])
            elif re.match(r'[?!:.,]', self.phone_seq[phone_number + 1]):
                pass
            # else, join all neighbouring phones to populate complete diphone list
            else:
                self.diphone_seq.append(('-'.join((self.phone_seq[phone_number], self.phone_seq[phone_number + 1]))))

    def get_phone_seq(self):
        # Get the input phrase's sequence of phones
        self.phone_seq = []
        pattern = r'\w+\'?\w+?|[?!:.,]+|\w+'
        # load the word to phones dictionary from nltk module
        self.phonedictionary = nltk.corpus.reader.cmudict.CMUDictCorpusReader.dict()
        # iterate through each word and valid punctuation in the input phase
        for word in nltk.tokenize.regexp_tokenize(self.phrase, pattern):
            # search each word in the phones dictionary, and append its phones to overall phone sequence
            # if args.spell is False:
            self.get_words_phones(word, self.phonedictionary)
            # # else, if spell command given, search each letter in the phones dictionary instead
            # else:
            # for letters in word:
            #   self.get_words_phones(letters, phonedictionary)
        # insert pause phones at the start and end of the phone sequence
        self.phone_seq.insert(0, 'PAU')
        self.phone_seq.append('PAU')

    def get_words_phones(self, word, phonedictionary):
        # look up a word's phones in the phone dictionary and append them to the phone sequence
        # if the word is punctuation, append the punctuation and a pause phone before and after
        if re.match(r'[?!:.,]', word):
            self.phone_seq.append('PAU')
            self.phone_seq.append(word)
            self.phone_seq.append('PAU')
        # if the spell command given, this allows program to ignore the individual apostrophe character
        elif word == '\'':
            pass
        # look for word in phone dictionary
        else:
            try:
                for phone in (phonedictionary[word][0]):
                    # remove numbers from the phones
                    phone = re.sub(r'\d', '', phone)
                    self.phone_seq.append(phone)
            # print error message alerting the user that they have entered an invalid word
            except KeyError:
                print('Sorry, {} isn\'t in my database. Please try another word or sentence.'.format(word))
                exit()

    def datetostring(self, phrase):
        # function for turning date to string of words
        # defining pattern to capture day month and year
        pattern = re.compile(r'(?P<day>\d{1,2})\/'  # Capture day
                             r'(?P<month>\d{1,2})\/?'  # Capture month
                             r'(?P<year>\d{2,4})?',  # Capture year
                             re.VERBOSE)
        for term in phrase.split():
            # check each term in the phrase to see if it is a date
            match_object = re.match(pattern, term)
            if match_object is not None:
                # if the term is a date, it will read its day and month
                # and replace them with an equivalent string of words
                day = self.num2places(int(match_object.group('day')))
                month = self.num2month(int(match_object.group('month')))
                if match_object.group('year') is None:
                    phrase = phrase.replace(term, re.sub(pattern, '{} {}'.format(month, day), term))
                # if a year is specified then it will convert it to a word
                else:
                    # if only the last two digits are specified, the system assumes 20th century
                    year = match_object.group('year')
                    if len(year) == 2:
                        year = self.num2words(int(year[-2:]))
                        phrase = phrase.replace(term,
                                                re.sub(pattern, '{} {} nineteen {}'.format(month, day, year), term))
                    # if four digits are specified, the system also reads the century
                    elif len(year) == 4:
                        century = self.num2words(int(year[0:2]))
                        year = self.num2words(int(year[-2:]))
                        phrase = phrase.replace(term,
                                                re.sub(pattern, '{} {} {} {}'.format(month, day, century, year), term))
        return phrase

    def digit2string(self, phrase):
        # replace digit in input string with a string word of digit
        for word in phrase.split():
            # found this lambda trick at https://stackoverflow.com/questions/9925230/regex-replace-in-python-convert-named-group-to-integer
            phrase = phrase.replace(word, re.sub(r'(?P<digit>\d)',
                                                 lambda x: self.num2words(int(x.group('digit')), digit='yes') + ' ', word))
        return phrase



    def num2month(self, n):
        # function for transforming integers to months
        num2monthdict = {1: 'january', 2: 'february', 3: 'march', 4: 'april', 5: 'may',
                         6: 'june', 7: 'july', 8: 'august', 9: 'september', 10: 'october',
                         11: 'november', 12: 'december'}
        try:
            return num2monthdict[n]
        except KeyError:
            # prints error message if a month is specified outside the range 1-12
            print('I can only accept 1-12 as a month of the year. Please try again.')
            exit()

    def num2places(self, n):
        # function for transforming integers to places
        num2placesdict = {1: 'first', 2: 'second', 3: 'third', 4: 'fourth', 5: 'fifth',
                          6: 'sixth', 7: 'seventh', 8: 'eighth', 9: 'ninth', 10: 'tenth',
                          11: 'eleventh', 12: 'twelfth', 13: 'thirteenth', 14: 'fourteenth',
                          15: 'fifteenth', 16: 'sixteenth', 17: 'seventeenth', 18: 'eighteenth',
                          19: 'nineteenth', 20: 'twentieth', 21: 'twenty first', 22: 'twenty second',
                          23: 'twenty third', 24: 'twenty fourth', 25: 'twenty fifth', 26: 'twenty sixth',
                          27: 'twenty seventh', 28: 'twenty eighth', 29: 'twenty ninth', 30: 'thirtieth',
                          31: 'thirty first'}
        try:
            return num2placesdict[n]
        except KeyError:
            # prints error message if a day is specified outside the range 1-31
            print('I can only accept 1-31 as a day of the month. Please try again.')
            exit()

    def num2words(self, n, digit=None):
        # function for transforming integers to word strings
        num2wordsdict = {0: 'hundred', 1: 'one', 2: 'two', 3: 'three', 4: 'four', 5: 'five',
                         6: 'six', 7: 'seven', 8: 'eight', 9: 'nine', 10: 'ten',
                         11: 'eleven', 12: 'twelve', 13: 'thirteen', 14: 'fourteen',
                         15: 'fifteen', 16: 'sixteen', 17: 'seventeen', 18: 'eighteen',
                         19: 'nineteen', 20: 'twenty', 30: 'thirty', 40: 'forty',
                         50: 'fifty', 60: 'sixty', 70: 'seventy', 80: 'eighty',
                         90: 'ninety'}
        # option to read 0 as zero instead of hundred, if number is not a year
        if digit == None:
            pass
        else:
            num2wordsdict[0] = 'zero'
        try:
            return num2wordsdict[n]
        except KeyError:
            try:
                return (num2wordsdict[n - n % 10] + ' ' + num2wordsdict[n % 10])
            except KeyError:
                # prints error message if a year is specified outside the range 1-99
                print('I can only accept years in the form YY or YYYY. Please try again.')
                exit()



def save_synth(phrase, file='audio.wav'):
    print(phrase)
    utt = Utterance(phrase)
    print('1')
    diphone_synth = Synth()
    print('2')
    diphone_synth.create_synthesis(utt.diphone_seq)
    print('3')
    diphone_synth.out.save(file)
    print('4')

# if __name__ == "__main__":
#     # create utterance from phrase, and synthesis from wav folder and utterance
#     utt = Utterance(args.phrase[0])
#     diphone_synth = Synth(wav_folder=args.diphones)
#     diphone_synth.create_synthesis(utt.diphone_seq)
#     if args.volume is not None:
#         # if volume is specified, rescale out amplitude accordingly
#         try:
#             diphone_synth.out.rescale(args.volume/100)
#         except ValueError:
#             print('Please specify a volume in the range 1-100.')
#             exit()
#     if args.play == True:
#         # if play command given, play audio
#         diphone_synth.out.play()
#     if args.outfile is not None:
#         # if save command given, save audio to outfile
#         diphone_synth.out.save(args.outfile)


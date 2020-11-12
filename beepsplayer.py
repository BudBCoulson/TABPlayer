#!/usr/bin/env python3

import os
import sys
import time
import math
import numpy as np
import simpleaudio as sa


class Player:
    def __init__(self, volume: float = 0.3,
                mute_output: bool = False):

        if volume < 0 or volume > 1:
            raise ValueError("Volume must be a float between 0 and 1")

        # Frequencies for the lowest octave
        self.note_frequencies =  {
            'A': 27.50000,
            'B': 30.86771,
            'C': 16.35160,
            'D': 18.35405,
            'E': 20.60172,
            'F': 21.82676,
            'G': 24.49971
        }

        self.volume = volume
        self.mute_output = mute_output
        self.rate = 44100
        self.fade = 800
        
        self._freqs = []
        self._harm = []
        self._joinmodes = []
        self._wavesegs = []
        self._comp = []
        
        self._valid_note = True
        self._fade_in = np.arange(0., 1., 1 / self.fade)
        self._fade_out = np.arange(1., 0., -1 / self.fade)
        self._play_obj = None
        self._audio = None
        self._destructor_sleep = 0

    def __set_base_frequency(self, note: str):
        if note == 'q':
            self._freqs.append(0)
            return

        if note == 'x':
            #placeholder 0 for now
            #need to account for string it's on
            #can't be treated as a simple freq
            #(same will be true for harmonics)
            self._freqs.append(0)
            return
		
        letter = note[:1].upper()
        try:
            self._freqs.append(self.note_frequencies[letter])
        except:
            self._valid_note = False
            print("Error: invalid note: '"
                                    + note[:1]
                                    + "'",
                                    file=sys.stderr)

    def __set_octave(self, octave: str = '4'):
        if not self._valid_note:
            return
        try:
            octaveValue = int(octave)
            if octaveValue < 0 or octaveValue > 8:
                raise ValueError('octave value error')
            self._freqs[-1] *= (2 ** octaveValue)
        except:
            self._valid_note = False
            print("Error: invalid octave: '"
                                    + octave
                                    + "'",
                                    file=sys.stderr)

    def __set_semitone(self, symbol: str):
        if not self._valid_note:
            return
        if symbol == '#':
            self._freqs[-1] *= (2 ** (1. / 12.))
        elif symbol == 'b':
            self._freqs[-1] /= (2 ** (1. / 12.))
        else:
            self._valid_note = False
            print("Error: invalid symbol: '"
                                    + symbol
                                    + "'",
                                    file=sys.stderr)

    def __calc_frequency(self, note: str):
        self.__set_base_frequency(note)
        if len(note) == 1:
            self.__set_octave()
        elif len(note) == 2:
            if note[1:2] == '#' or note[1:2] == 'b':
                self.__set_octave()
                self.__set_semitone(note[1:2])
            else:
                self.__set_octave(note[1:2])
        elif len(note) == 3:
            self.__set_octave(note[1:2])
            self.__set_semitone(note[2:3])
        else:
            if self._valid_note:
                print("Errror: invalid note: '"
                                        + note
                                        + "'",
                                        file=sys.stderr)
                self._valid_note = False

    def __wait_for_prev_sound(self):
        if self._play_obj is not None:
            while self._play_obj.is_playing(): pass
            
    def __gen_waveseg(self, freq: float, harm: bool, stime: float, etime: float):
        dur = etime - stime
        t = np.linspace(stime, etime, int(dur * self.rate), False)
        wave = np.sin(freq * t * 2 * np.pi)
        if not harm:
            wave += sum([np.sin(mul * freq * t * 2 * np.pi)/2**(mul-1) for mul in range(2,6)])
        self._wavesegs.append(wave)	
        
    def __gen_bend(self, f0: float, f1: float, stime: float, etime: float):
        dur = etime - stime
        t = np.linspace(stime, etime, int(dur * self.rate), False)
        wave = np.sin(np.pi * ((f1-f0) * np.square(t) / dur + f0 * t * 2))
        self._wavesegs.append(wave)
		
    def __overlay(self): #this doesn't need to be its own fcn
		#overlays over time interval
        self._audio = sum(self._comp)
            
    def __gen_waveform(self, dur: float):
		#for each pair of notes: generate a wave connecting them approp.
		#for first and last note: extra half-len segm. at ends
		#(this sounds bad for bend/slide)
		#right now isn't doing all slides correctly, assumes all are 'to'
        unitl = dur/4
        nnotes = len(self._freqs)
        tot = 2 * unitl * nnotes

        f0 = self._freqs[0]
        h0 = self._harm[0]
        self.__gen_waveseg(f0,h0,0,unitl)

        for i in range(nnotes-1):
            f1 = self._freqs[i+1]
            h1 = self._harm[i+1]
            mode = self._joinmodes[i]

            if mode in ['n','h','p']:
                self.__gen_waveseg(f0,h0,(2*i+1)*unitl,(2*i+2)*unitl)
                self.__gen_waveseg(f1,h1,(2*i+2)*unitl,(2*i+3)*unitl)

            elif mode in ['b','^','r']:
                self.__gen_bend(f0,f1,(2*i+1)*unitl,(2*i+3)*unitl)
                
            elif mode in ['\\','/','s']:
                fund = (2 ** (1. / 12.))
                steps = int(math.log(f1/f0,fund))
                ud = -(-1)**(steps>0)
                steps *= ud
                self.__gen_waveseg(f0,h0,(2*i+1)*unitl,(2*i+1.2)*unitl)
                j = 0
                for j in range(1,steps):
                    f = f0*fund**(ud*j)
                    self.__gen_waveseg(f,False,(2*i+1.1+.1*j)*unitl,(2*i+1.2+.1*j)*unitl)
                self.__gen_waveseg(f1,h1,(2*i+1.2+.1*j)*unitl,(2*i+3)*unitl)
                
            f0, h0 = f1, h1   
					
        self.__gen_waveseg(f1,h1,tot-unitl,tot)

        self._comp.append(np.concatenate(self._wavesegs))
	
        '''
        if mode in ['n','x']: #regular notes/chords
            self.comp.append(self.__wave_horiz(dur,self.freqs)[0])
        if mode == 'hp': #hammer-on/pull-off
            #equal duration for each component note
            dur *= len(self.freqs)/2
            self.comp.append(np.concatenate(self.__wave_horiz(dur, self.freqs)))
        if mode == 'st': #slide to a note (from another note or nowhere)
            #allocate half the duration to end note
            #2DO - if from nowhere, ramp up from 0 to full volume over slide
            rest = 1 - (len(self.freqs)-1)/5
            self.comp.append(np.concatenate(
                             self.__wave_horiz(dur/5,[self.freqs[0]])+
                             self.__wave_horiz(dur*(1-rest-.2),self.freqs[1:-1])+
                             self.__wave_horiz(dur*rest,[self.freqs[-1]])))
        if mode == 'sa': #slide away from a note (to nowhere)
            #allocate half the duration to start note
            #2DO - drop off from full volume to 0 over slide
            rest = 1 - (len(self.freqs)-1)/5
            self.comp.append(np.concatenate(
                             self.__wave_horiz(dur*rest,[self.freqs[0]])+
                             self.__wave_horiz(dur*(1-rest-.2),self.freqs[1:-1])+
                             self.__wave_horiz(dur/5,[self.freqs[-1]])))
        if mode == 'b': #bend
            #transtition continuously up, suddenly for release
            f0, f1 = self.freqs
            t = np.linspace(0, dur, int(dur * self.rate), False)
            self.comp.append(np.sin(np.pi * ((f1-f0) * np.square(t) / dur 
                                 + f0 * t * 2)))
        '''      

    def __write_stream(self):
        audio = self._audio
        audio *= 32767 / np.max(np.abs(audio))
        audio *= self.volume

        if len(audio) > self.fade:
            audio[:self.fade] *= self._fade_in
            audio[-self.fade:] *= self._fade_out

        audio = audio.astype(np.int16)

        self.__wait_for_prev_sound()
        self._play_obj = sa.play_buffer(audio, 1, 2, self.rate)

    def __print_played_notes(self, notes: [str], dur: float, mode: str = 'n'):
        #need to change behavior here to allow for the fancier stuff
        if self.mute_output or not self._valid_note:
            return
        if mode == 'n':
            if len(notes) == 1:
                note = notes[0]
                if note == 'pause':
                    print("Pausing for " + str(dur) + "s")
                else:
                    print("Playing note " + note + 
                          " for " + str(dur) + "s")
            else:
                print("Playing chord " + ','.join(notes) + 
                      " for " + str(dur) + "s")
        elif mode == 'l':
            print("Playing legato " + ','.join(notes) + 
                  " for " + str(dur) + "s")
        elif mode == 'b':
            print("Playing bend " + ','.join(notes) + 
                  " for " + str(dur) + "s")
    
    def __param_reset(self):
        self._freqs = []
        self._joinmodes = []
        self._wavesegs = []

    def play_note(self, notes: [[str]], dur: float = 0.5):
        print(notes) #DISPLAY
        self.__param_reset()
        self._comp = []
        self._audio = None
        self._valid_note = True
        if notes == [['q']]:
            self.__wait_for_prev_sound()
            #self.__print_played_notes(notes, dur)
            time.sleep(dur)
            self._destructor_sleep = 0
            
        else:
            for unit in notes:
                for sym in unit:
                    if sym[0][0] in ['A','B','C','D','E','F','G','x','q']:
                        self.__calc_frequency(sym[0])
                        self._harm.append(True)#sym[1])
                    else:
                        self._joinmodes.append(sym)
                if self._valid_note:               
                    self.__gen_waveform(dur)
                    self.__param_reset()
                    
            if self._valid_note:
                self.__overlay()
                self.__write_stream()
                #self.__print_played_notes(notes, dur, mode)
                self._destructor_sleep = dur #adjust this

    def __del__(self):
        time.sleep(self._destructor_sleep)

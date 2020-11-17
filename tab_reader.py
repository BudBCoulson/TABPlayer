import musicalbeeps
import re
import math
import threading
#import time

'''
This project's goal is to be able to download an ASCII guitar TAB directly from the internet and play it without pre-editing
Intractable issues:
-- Note spacing info can't always be read directly
-- Often riffs for multiple guitars are interspersed
-- Can't tell when a given bar needs to be repeated without much more advanced parsing
-- Past the basics, notation is inconsistent
'''


tones = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
#convert flat notes to equivalent sharp or natural. Unnecessary?
unflat = {'Bb': 'A#', 'Db': 'C#', 'Eb': 'D#', 'Fb': 'E', 'Gb': 'F#', 'Ab': 'G#'}
#give harmonic overtone multiplier (approximate)
harmonics = {0: 0, 1: 16, 2: 9, 3: 6, 4: 5, 5: 4, 6: 7, 7: 3, 8: 8, 9: 5, 10: 9, 11: 15, 12: 2,
             13: 32, 14: 9, 15: 12, 16: 5, 17: 8, 18: 14, 19: 3, 20: 16, 21: 10, 22: 18, 23: 15, 24: 4}
#freqs = [130.81, 138.59, 146.83, 155.56, 164.81, 174.61, 185, 196, 207.65, 220, 233.08, 246.94] #This is 3rd octave


#freqs = [2*f for f in freqs] #for better winsound
#fdict = dict(zip(tones,freqs))

#h = hammer-on. Join two notes into half-dur waves spliced midway.
#p = pull-off. Same as h but second half has slight volume increase?
#\, /, s = slide. Similar to above but goes over all in-between tones.
#b,^ = bend. Always up, up to a full tone. Here do continuous (instead of discrete) frequency transition.
#r = release bend.
#v, ~ = vibrato. Rapid bend/release.
#= = extend. Hold note.
#*, +, <> = harmonic. Pure tone, according to dict.
#x = dead note. Soften/dampen volume?
#() = ghost note. Play softer?

#currently I'm not using this list directly
symb = ['h','p','b','r','s','v','x','^','~','\\','/','(',')','[',']','<','>','*','+','=','-']


def clean(tabfile,printout=False):
	
	'''
	Processes ASCII tab into playable format.
	
	#right now output isn't implemented until I'm done converting things to the new paradigm
	For output text:
	-- eliminates non-essential characters
	-- annotates string tunings with base octave numbers
	-- eliminates line breaks, putting notes onto long continuous "strings"
	-- Changes fret numbers into hexidecimal for help with timing spacing
	
	For internal reading:
	-- stores string tunings, fret numbers played on each string, and separation between notes

	Assumptions:
	-- No key changes throughout
	-- Just newlines between bars (no spaces) - this can be dealt with using regex?
	-- Only single legato transitions instead of multiple
	'''

	tunings = ['']*6 #stores tunings of the strings
	strings = [[] for _ in range(6)] #stores notes on the six strings of the tab
	#nlines = ['']*6 #stores modified tab to write to new file if needed
	nidxs = [-1]*6 #indices along each string
	sidx = 0 #index of current string
	#tenflag = False #for handling 2-digit frets
	#slideflag = False #for handling slides
	#hpflag = False #for handling hammer-ons/pull-offs
	slflag = False
	newbarfl = True
	init = True

	with open('Tabs\\'+tabfile+'.txt', 'r') as f:
		
		for line in f:
			
			noteunit = pnu = ''
			stexp = pse = 0
			
			#this should mean we've reached the end legend
			if line[0] in ['*', '-', '=']: 
				break
			
			#no longer the first bar, move to next bar
			#skip over any intermediary instructions
			if line[0] in ['\n', ' ', '[', '(', '|']:
				if not newbarfl:
					for i in range(6):
						nidxs[i] -= 3 
					newbarfl = True
				continue
			newbarfl = False
			
			if tunings[-1]:
				init = False
				
			#altered = ''
			for i, ch in enumerate(line):
				
				nidxs[sidx] += 1
				
				if slflag:
					slflag = False
					continue
				
				if init and i<2 and (ch.isalpha() or ch == '#'): #get string tunings
					if i == 0: #capitalize note but not accidentals
						tunings[sidx] += ch.upper()
					else:
						tunings[sidx]+=ch
				
				elif not init and i<2: #skip string tunings on later bars
					continue
				
				
				#treat things uniformly: always track lists of frets, 
				#push onto stack when seeing something that couldn't be part of an extended fret notation (e.g., '-')
				#with this approach, don't need most of the flags
				#instead have separate helper function to process these individual units
				
				elif ch == '|':
					nidxs[sidx] -= 0#2
				
				elif ch != '-':
					if not noteunit:
						stexp = nidxs[sidx]
					noteunit += ch
						
				else: #ch == '-'
					#handle spaced slide (iron man)
					if noteunit in ['\\','/']:
						strings[sidx].pop()
						noteunit, stexp = pnu, pse
						slflag = True
					#do something similar for release after (invisibly) held bend?
					#see heart shaped box for example
					elif noteunit:
						pnu, pse = noteunit, stexp
						fm = [stexp,nidxs[sidx],peeler(noteunit)]
						strings[sidx].append(fm)
						noteunit = ''
						stexp = 0
					
				
				'''
				elif ch.isdigit(): #(part of) a fret
					if hflag:
						#altered += hex(10+int(ch))[2:] #compensate for overwritten '-'
						tracknote[0].append(10+int(ch))
						notestr += hex(10+int(ch))[2:]
						#strings[sidx].append([nidxs[sidx],10+int(ch)])
						hflag = False
						
					elif ch == '1': #could be 10s place of a 2-digit fret, have to look at next position
						hflag = True
						continue
					
					else:
						#altered += ch
						fret = int(ch)
						if slideflag:
							slideflag = False
							if tracknote[0]
							#[t,pfret] = strings[sidx].pop()
							#strings[sidx].append([t,slider(pfret,fret),'l'])
						elif hpflag:
							hpflag = False	
							#[t,pfret] = strings[sidx].pop()
							#strings[sidx].append([t,[pfret,fret],'l'])
						else:
							#strings[sidx].append([nidxs[sidx],fret])
					
				elif hflag:
					altered += '1-'
					strings[sidx].append([nidxs[sidx]-1,1])
					hflag = False
				
				#this is where extra notation things are handled
				else: 
					if ch in symb:
						altered += ch
						if ch in ['h','p']:
							hpflag = True
						if ch in ['\\','/']:
							slideflag = True
						if ch == 'b':
							#assume half-tone bends by default (for now, adjust this by hand per song)
							[t,fret] = strings[sidx].pop()
							strings[sidx].append([t,[fret,fret+1],'b'])
					if ch == '|': #these happen between sections of the same bar, mess up timings
						altered = altered[:-1]
						nidxs[sidx] -= 2
						#skipflag = True
				'''

			#nlines[sidx] += altered
			sidx = (sidx+1)%6
	
	for i in range(6):
		if tunings[i] in unflat:
			tunings[i] = unflat[tunings[i]]
		octave = 3-(i-1)//3
		for nrec in strings[i]:
			nrec += [tunings[i],octave]
		tunings[i] += str(octave)
		
	#if printout:
	#	nlines = [tunings[i]+nlines[i]+'\n' for i in range(6)]
	#	with open('Tabs\\Modified\\'+tabfile+'_mod.txt', 'w') as f:
	#		f.writelines(nlines)
			
	return strings
	
def peeler(noteunit):
	'''Does some preprocessing of fret+extras sequences'''
	#what I'm allowing for:
	#single-digit and two-digit single frets and chords
	#chains of hammer-ons/pull-offs/bends/releases/slides
	#phantom slide: / or \ paired with a single fret on either side?
	
	#implement now:
	#harmonic <> (actually this is what I have currently, should instead do overtones for other notes)
	#ghost notes ()? Just ignore, always play these
	#dead note x (don't fully understand - obtain by solving diff eq?)
	#extended notes =/vibrato v~
	
	symb = re.split(r'(\d+)',noteunit)
	
	#old version: fret list with mode
	'''
	frets = []
	mode = 'n'
	sl = 0
	
	for f in symb:
		if f.isdecimal():
			fret = int(f)
			if sl:
				if not frets: #slide from nowhere
					frets.append(fret - sl*2)
				sl = 0
			frets.append(fret)
		elif f == 'x':
			frets.append(0)
			mode = 'x'
		elif f == 'b':
			mode = 'b'
		elif f in ['h','p']:
			mode = 'hp'
		elif f in ['\\','/']:
			sl = 1 if f == '/' else -1
			mode = 'st'
	
	if sl:
		mode = 'sa'
		frets.append(fret + sl*2)
		
	if mode in ['st', 'sa']:
		frets = slider(*frets)
		
	return [mode, frets]
	'''
	
	#new version: list of interspersed frets and/or connectors
	#pushing most of the real work off to MB side
	#change: track harmonics by bumping up fret #
	#(keep bools for now too so as to also incorp. overtones)
	#also right now I'm just putting in slashes and not tracking phantom
	#add support for ~, =
	
	playarr = []
	sl = 0
	be = 0
	rel = 0
	fret = pfret = None
	harm = False
	
	for f in symb:
		if f.isdecimal():
			fret = int(f)
			if sl:
				if len(playarr) == 1: #slide from nowhere
					slchar = '/' if sl > 0 else '\\'
					playarr = [[fret - sl*3,False], slchar]
				sl = 0
			if be:
				if len(playarr) == 1:
					playarr = [[fret-1,False], 'b']
				be = 0
			if rel:
				if len(playarr) == 1:
					playarr = [[fret+1,False], 'r']
				rel = 0
			
			if harm:
				playarr.append([(harmonics[fret]-1)*12,True])
			else:
				playarr.append([fret,False])
				
		elif f:
			if f == 'x':
				#temporary
				playarr.append([60,False])
			elif f in ['h','p']:
				playarr.append(f)
			elif f in ['<','[']:
				harm = True
			elif f == ['>',']']:
				harm = False
			elif f == '"':
				harm = not harm
			elif f in ['*','+']:
				playarr[-1] = [fret,True]
			elif f in ['\\','/','s']:
				sl = 1 if f == '/' else -1
				playarr.append(f)
			elif f in ['b','^']:
				pfret = fret
				be = 1
				playarr.append(f)
			elif f == 'r':
				if pfret:
					if be:
						playarr.extend([[pfret+be,False],'r',[pfret,False]])
					else:
						playarr.extend(['r',[pfret,False]])
					playarr.append(f)
				else:
					rel = -1
				playarr.append(f)

			
	if sl:
		playarr.append([fret + sl*3,False])
	if be:
		playarr.append([fret + be,False])
	if rel:
		playarr.append([fret + rel, False])
	
	return playarr
	

def slider(startfret, endfret):
	
	'''Converts endpoints of a slide into whole interval'''
	#no longer used?
	
	slidedir = -(-1)**(endfret>startfret)
	return list(range(startfret, endfret+slidedir,slidedir))
	
def padder(noteslist):
	
	'''Makes sure all note components have the same length'''
	#keep in mind that note components can have other symbols now too
	#do I want to add extra blank or hold note?\
	#this just isn't working in the cases it's supposed to handle
	
	l = max([len(notecomp) for notecomp in noteslist])
	for notecomp in noteslist:
		n = len(notecomp)
		sy = 'q' #for 'quiet'
		#for sy in reversed(notecomp):
		#	if isinstance(sy,int):
		#		break
		notecomp += [sy]*(l-n)

#freq conv. function, no longer used
'''
def freqconv(tone, fret):
	
	''''''Converts tone+fret to frequency''''''
	
	idx = tones.index(tone)
	nidx = (idx + fret)
	omult = 2**(nidx // 12)
	nidx %= 12
	return fdict[tones[nidx]]*omult
'''
	
def noteconv(fret, tone, octave):
	
	'''Converts tone, fret, octave to MB note format'''
	
	idx = tones.index(tone)
	nidx = (idx + fret)
	octave += nidx // 12
	nidx %= 12
	
	note = tones[nidx]
	note = note[0]+str(octave)+note[1:]
	return note 
	
def ncmap(fretl, tone, octave):
	
	'''Maps noteconv over just the fret numbers (integers) of a noteset'''
	
	noteset = []
	
	for f in fretl:
		if isinstance(f,list):
			fret = f[0]
			noteset.append([noteconv(fret,tone,octave),f[1]])
		else:
			noteset.append(f)
	
	return noteset

def playtab(tabfile,note_len=.5):
	
	'''
	A program to play songs written out on ASCII guitar tabs

	To do:
	-- Extended notes/vibrato
	-- Longer tapping chains

	-- Better sound system (actual guitar tones)
	
	-- parallel threads: one for each string!
	'''
	
	note_times = clean(tabfile)
	print(note_times)
	
	note_sequence = sorted([note for string_notes in note_times for note in string_notes])
	note_sequence = [(ts,te,ncmap(frets,tone,octave)) for ts,te,frets,tone,octave in note_sequence]
	
	pts = pte = 0
	notes_list = []
	sound_sequence = []
	sum_spacing = 0
	for ts, te, notel in note_sequence:
		if len(notel) == 1:
			notel = notel + ['n'] + notel
		if pts == ts:
			notes_list.append(notel)
		else:
			if pts:
				padder(notes_list)
				sound_sequence.append((pts,pte,notes_list))
				sum_spacing += ts-pte
			pts, pte = ts, te
			notes_list = [notel]
	padder(notes_list)
	sound_sequence.append((pts,pte,notes_list))
	
	avg_spacing = sum_spacing/len(sound_sequence)
	print('as',avg_spacing)
	
	#should now always be of the form of interspersed notes and modes
	#moreover, all should have been padded to the same length
	#and the minimum length is three (one note unit with connector) 
	for ss in sound_sequence:
		print(ss)
		
	#musicalbeep
	player = musicalbeeps.Player(volume = 0.8, mute_output = False)
	pt = 0
	pause_sp = math.ceil(avg_spacing / 2)
	
	#timing cheat for HotRS
	hotrs = 0
	
	for ts, te, nestnotes in sound_sequence:
		#adjust this based on song
		
		#works for some others
		#pause = (t-pt-3*spacing)*note_len
		
		#works for BB
		#if ts - pte > 2:
		#	player.play_note([['q']],.1)
		
		pa = (ts - pte)/pause_sp - 1
		if pa > 1:
			player.play_note([['q']],note_len*pa/2)
		
		pte = te
		#if pause > 0:
		#	player.play_note([['pause']],pause,'n')
		fast = 1
		#if hotrs in [1,2,3]:
		#	fast = 2
		
		player.play_note(nestnotes,note_len/fast)
		
		#hotrs += 1
		#hotrs %= 7

def sample(i,notelen):	
	tabfiles = ['basic_scale_c_minor', 'twinkle_star', 'sweet_child_o_mine_intro', 
	            'livin_on_a_prayer_intro', 'more_than_a_feeling_intro', 'chopsticks', 
	            'blackbird', 'iron_man', 'snow_hey_oh', 'yellow_ledbetter', 
	            'heart_shaped_box', 'house_of_the_rising_sun', 'plug_in_baby',
	            'hysteria', 'whole_lotta_love', 'scar_tissue', 'paint_it_black',
	            'dont_fear_the_reaper', 'thunderstruck', 'smoke_on_the_water',
	            'raining_blood', 'jessica', 'cowboys_from_hell', 'hangar_18', 'chop_suey',
	            'you_really_got_me', 'the_trooper', 'comfortably_numb_solos',
	            'nothing_else_matters', 'red_barchetta', 'roundabout', 'fur_elise']
			
	playtab(tabfiles[i],notelen)
	
#issues tracker
#for everything, issue with chord slide arrays being incompat due to dimn off by 1 (only for certain notelen)
#(this happens with slides/bends due to rounding from splitting/squaring?)
#iron man has a hammer onto nothing '9h'
#heart shaped box & hysteria has held bend into release (sep by -)
#plug in baby didn't play final bend-rel
#whole lotta love has bend from nothing
#thunderstruck doesn't process init. riff at all
#often tripped up by "o"s to indicate repeated bars

#2Do finish:
#finish harmonics, calc. and implement muted
#repair all outstanding issues in all songs above


'''
player = musicalbeeps.Player(volume = 0.9, mute_output = False)
player.play_note([[['A3',False],'n',['A3',False]]],1)
'''


sample(23,.1)

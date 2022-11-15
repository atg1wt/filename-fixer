#!/usr/bin/env python

# Filename Fixer (c) 2022-11-15 by Tyrone C.
# Tool for bulk-fixing filenames
# Run it, drag multiple files onto it, change "New names" to suit, then hit "Rename Files"
# Requires python 3.8+

import os
import re
import wx

# Class for panel which contains all the controls

class FixerPanel(wx.Panel):

	def __init__(self, parent): 
		super(FixerPanel, self).__init__(parent)
		self.add_widgets()
		self.undo_stack = []
		
	def add_widgets(self):
		# widget border sizes
		LARGE = 8
		SMALL = 4
		
		# create a vertical sizer to hold everything else
		vsiz = wx.BoxSizer(wx.VERTICAL)
		
		# directory name
		hsiz_dir = wx.BoxSizer(wx.HORIZONTAL)
		hsiz_dir.Add(wx.StaticText(self, label='Directory:'), flag = wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border = SMALL)
		self.dir = wx.TextCtrl(self, style = wx.TE_READONLY)
		hsiz_dir.Add(self.dir, proportion = 1)
		
		# labels for filename lists
		hsiz_labels = wx.BoxSizer(wx.HORIZONTAL)
		hsiz_labels.Add(wx.StaticText(self, label = 'Old Names:'), proportion = 1, flag = wx.EXPAND)
		hsiz_labels.Add(wx.StaticText(self, label = 'Numbers:', size=(80,0)), flag = wx.EXPAND)
		hsiz_labels.Add(wx.StaticText(self, label = 'New Names:'), proportion = 1, flag = wx.EXPAND)
		hsiz_labels.Add(wx.StaticText(self, label = 'Extensions:', size=(80,0)), flag = wx.EXPAND)
		
		# filename lists
		hsiz_files = wx.BoxSizer(wx.HORIZONTAL)
		self.src = wx.TextCtrl(self, style = wx.TE_MULTILINE | wx.TE_DONTWRAP | wx.TE_READONLY)
		self.trk = wx.TextCtrl(self, style = wx.TE_MULTILINE | wx.TE_DONTWRAP, size = (80,0) )
		self.dst = wx.TextCtrl(self, style = wx.TE_MULTILINE | wx.TE_DONTWRAP)
		self.ext = wx.TextCtrl(self, style = wx.TE_MULTILINE | wx.TE_DONTWRAP | wx.TE_READONLY, size = (80,0) )
		hsiz_files.Add(self.src, proportion = 1, flag = wx.EXPAND)
		hsiz_files.Add(self.trk, flag = wx.EXPAND)
		hsiz_files.Add(self.dst, proportion = 1, flag = wx.EXPAND)
		hsiz_files.Add(self.ext, flag = wx.EXPAND)

		# fix background colours for readonly multiline textboxes
		bkg = wx.SystemSettings.GetColour(wx.SYS_COLOUR_FRAMEBK)
		self.src.SetBackgroundColour(bkg)
		self.ext.SetBackgroundColour(bkg)
		
		# 1) Trim IDs / track numbering
		hsiz_firsts = wx.BoxSizer(wx.HORIZONTAL)
		btn = wx.Button(self, label = "Trim BBC PIDs")
		btn.SetToolTip("Removes any suffixes added by get_iplayer.")
		btn.Bind(wx.EVT_BUTTON, self.trim_iplayer)
		hsiz_firsts.Add(btn, flag = wx.RIGHT, border = LARGE)
		btn = wx.Button(self, label = "Trim YouTube IDs")
		btn.SetToolTip("Removes any suffixes added by youtube-dl.")
		btn.Bind(wx.EVT_BUTTON, self.trim_youtube)
		hsiz_firsts.Add(btn, flag = wx.RIGHT, border = LARGE)
		
		hsiz_firsts.AddStretchSpacer()

		btn = wx.Button(self, label = "Undo")
		btn.SetToolTip("Undoes changes to new names and track numbers made by command buttons.")
		btn.Bind(wx.EVT_BUTTON, self.undo)
		hsiz_firsts.Add(btn, flag = wx.RIGHT, border = LARGE)

		hsiz_firsts.AddStretchSpacer()

		btn = wx.Button(self, label = "Extract track numbers")
		btn.SetToolTip("Separates out track numbers from names.")
		btn.Bind(wx.EVT_BUTTON, self.extract_numbers)
		hsiz_firsts.Add(btn, flag = wx.RIGHT, border = LARGE)
		btn = wx.Button(self, label = "Auto-number")
		btn.SetToolTip("Numbers tracks from 1 in the order listed.")
		btn.Bind(wx.EVT_BUTTON, self.auto_number)
		hsiz_firsts.Add(btn, flag = wx.RIGHT, border = LARGE)
		btn = wx.Button(self, label = "Number by mod dates")
		btn.SetToolTip("Sets track numbers in order of file modification time.")
		btn.Bind(wx.EVT_BUTTON, self.number_by_mod_date)
		hsiz_firsts.Add(btn, flag = wx.RIGHT, border = LARGE)
		btn = wx.Button(self, label = "Number by text dates")
		btn.SetToolTip("Sets track numbers in order of datestamps left in filenames by SingleFile browser extension.")
		btn.Bind(wx.EVT_BUTTON, self.number_by_date_in_filename)
		hsiz_firsts.Add(btn)
				
		# 2) Find and trim common prefix and suffix
		hsiz_commons = wx.BoxSizer(wx.HORIZONTAL)
		hsiz_commons.Add(wx.StaticText(self, label='Common Prefix:'), flag = wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border = SMALL)
		self.prefix = wx.TextCtrl(self)
		hsiz_commons.Add(self.prefix, proportion = 1, flag = wx.RIGHT, border = LARGE)
		hsiz_commons.Add(wx.StaticText(self, label='Common Suffix:'), flag = wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border = SMALL)
		self.suffix = wx.TextCtrl(self)
		hsiz_commons.Add(self.suffix, proportion = 1, flag = wx.RIGHT, border = LARGE)
		btn = wx.Button(self, label="Detect")
		btn.SetToolTip("Looks for a prefix and suffix common to all filenames.")
		btn.Bind(wx.EVT_BUTTON, self.find_common)
		hsiz_commons.Add(btn, flag = wx.RIGHT, border = LARGE)
		btn = wx.Button(self, label = "Trim")
		btn.SetToolTip("Removes the specified prefix and suffix from filenames, where present.")
		btn.Bind(wx.EVT_BUTTON, self.trim_common)
		hsiz_commons.Add(btn)
		
		# 3) Other search and replace
		hsiz_search = wx.BoxSizer(wx.HORIZONTAL)
		hsiz_search.Add(wx.StaticText(self, label = 'Find:'), flag = wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border = SMALL)
		self.find_str = wx.TextCtrl(self)
		hsiz_search.Add(self.find_str, proportion = 1, flag = wx.RIGHT, border = LARGE)
		hsiz_search.Add(wx.StaticText(self, label = 'Replace:'), flag = wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border = SMALL)
		self.replace_str = wx.TextCtrl(self)
		hsiz_search.Add(self.replace_str, proportion = 1, flag = wx.RIGHT, border = LARGE)
		self.chk_regex = wx.CheckBox(self, label = "RegEx")
		self.chk_regex.SetToolTip("If checked, uses regular expressions rather than text replacement.")
		hsiz_search.Add(self.chk_regex, flag = wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border = SMALL)
		self.chk_case = wx.CheckBox(self, label = "Match Case")
		hsiz_search.Add(self.chk_case, flag = wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border = SMALL)
		btn = wx.Button(self, label = "Replace")
		btn.SetToolTip("Finds instances of one string and replaces them with the other.")
		btn.Bind(wx.EVT_BUTTON, self.replace)
		hsiz_search.Add(btn)
		
		# 5) Space and case
		csiz_cleanup = wx.BoxSizer(wx.HORIZONTAL)
		self.chk_fullstop = wx.CheckBox(self, label = "Convert full stops to spaces")
		csiz_cleanup.Add(self.chk_fullstop, flag = wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border = SMALL)
		self.chk_hyphen = wx.CheckBox(self, label = "Convert hyphens to spaces")
		csiz_cleanup.Add(self.chk_hyphen, flag = wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border = SMALL)
		self.chk_camel = wx.CheckBox(self, label = "Convert camel case")
		self.chk_camel.SetToolTip("If checked, a capital letter following a lower-case letter will be treated as the start of a new word and spaced accordingly.")
		csiz_cleanup.Add(self.chk_camel, flag = wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border = SMALL)
		self.chk_all_caps = wx.CheckBox(self, label = "Convert individual all-caps words")
		self.chk_all_caps.SetToolTip("If checked, individual all-caps words in a mixed-case string will be converted to title case; otherwise these words will be left uppercase.")
		csiz_cleanup.Add(self.chk_all_caps, flag = wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border = SMALL)
		csiz_cleanup.AddStretchSpacer()
		btn = wx.Button(self, label = "Space and Case")
		btn.SetToolTip("Tries to fix word breaks and letter case")
		btn.Bind(wx.EVT_BUTTON, self.cleanup)
		csiz_cleanup.Add(btn)

		# 6) Rename and go
		hsiz_cmds = wx.BoxSizer(wx.HORIZONTAL)
		hsiz_cmds.AddStretchSpacer()
		btn = wx.Button(self, label = "Rename Files")
		btn.SetToolTip("Renames the files to the new names")
		btn.Bind(wx.EVT_BUTTON, self.rename)
		hsiz_cmds.Add(btn, flag = wx.RIGHT, border = LARGE)
		btn = wx.Button(self, label = "Exit")
		btn.Bind(wx.EVT_BUTTON, self.exit)
		hsiz_cmds.Add(btn)
		
		# put horizontal sizers in the vertical one
		vsiz.Add(hsiz_dir, flag = wx.EXPAND | wx.ALL, border = LARGE)
		vsiz.Add(hsiz_labels, flag = wx.EXPAND | wx.TOP | wx.LEFT | wx.RIGHT, border = LARGE)
		vsiz.Add(hsiz_files, flag = wx.EXPAND | wx.BOTTOM | wx.LEFT | wx.RIGHT, proportion = 1, border = LARGE)
		vsiz.Add(hsiz_firsts, flag = wx.EXPAND | wx.ALL, border = LARGE)
		vsiz.Add(hsiz_commons, flag = wx.EXPAND | wx.ALL, border = LARGE)
		vsiz.Add(hsiz_search, flag = wx.EXPAND | wx.ALL, border = LARGE)
		vsiz.Add(csiz_cleanup, flag = wx.EXPAND | wx.ALL, border = LARGE)
		vsiz.Add(hsiz_cmds, flag = wx.EXPAND | wx.ALL, border = LARGE)
		
		# attach vertical sizer to panel
		vsiz.SetSizeHints(self)
		self.SetSizer(vsiz)

	def get_old_names(self):
		return self.src.GetValue().split("\n")
		
	def get_new_names(self):
		return self.dst.GetValue().split("\n")

	def get_nums(self):
		return self.trk.GetValue().split("\n")

	def get_exts(self):
		return self.ext.GetValue().split("\n")

	def get_dir(self):
		return self.dir.GetValue()

	def set_old_names(self, names):
		self.src.SetValue("\n".join(names))

	def set_new_names(self, names):
		self.dst.SetValue("\n".join(names))

	def set_nums(self, nums):
		self.trk.SetValue("\n".join(nums))

	def set_exts(self, exts):
		self.ext.SetValue("\n".join(exts))

	def set_dir(self, dir):
		self.dir.SetValue(dir)

	def save_for_undo(self):
		names = self.get_new_names()
		nums = self.get_nums()
		self.undo_stack.append((names, nums))

	def undo(self, e):
		if len(self.undo_stack):
			(names, nums) = self.undo_stack.pop()
			self.set_new_names(names)
			self.set_nums(nums)

	def populate_from_drop(self, files):
		files.sort(key = lambda x: x.casefold())
		# build lists for text controls
		names = list()
		exts = list()
		for file in files:
			base = os.path.basename(file)
			(name,ext) = os.path.splitext(base)
			names.append(name)
			exts.append(ext)
			dir = os.path.dirname(file)
		# populate text controls
		self.set_old_names(names)
		self.set_new_names(names)
		self.set_exts(exts)
		self.set_nums([''] * len(names))
		# make sure dir ends with separator
		if (dir[-1:] != os.sep):
			dir = dir + os.sep
		self.set_dir(dir)
		# clear the undo history
		self.undo_stack = []

	def find_common(self, e):
		names = self.get_new_names()
		(prefix, suffix) = FixerUtils.find_common(names)
		self.prefix.SetValue(prefix)
		self.suffix.SetValue(suffix)

	def trim_common(self, e):
		self.save_for_undo()
		names = self.get_new_names()
		prefix = self.prefix.GetValue()
		suffix = self.suffix.GetValue()
		names = FixerUtils.trim_common(names, prefix, suffix)
		self.set_new_names(names)

	def trim_iplayer(self, e):
		self.save_for_undo()
		names = self.get_new_names()
		names = FixerUtils.trim_iplayer(names)
		self.set_new_names(names)
		# files are from get_iplayer, so assume we want to replace full stops
		self.chk_fullstop.SetValue(wx.CHK_CHECKED)

	def trim_youtube(self, e):
		self.save_for_undo()
		names = self.get_new_names()
		names = FixerUtils.trim_youtube(names)
		self.set_new_names(names)

	def extract_numbers(self, e):
		self.save_for_undo()
		names = self.get_new_names()
		(names, nums) = FixerUtils.extract_numbers(names)
		self.set_new_names(names)
		self.set_nums(nums)

	def number_by_mod_date(self, e):
		self.save_for_undo()
		names = self.get_old_names()
		exts = self.get_exts()
		(nums) = FixerUtils.number_by_mod_date(self.get_dir(), names, exts)
		self.set_nums(nums)

	def number_by_date_in_filename(self, e):
		self.save_for_undo()
		names = self.get_new_names()
		(names, nums) = FixerUtils.number_by_date_in_filename(names)
		self.set_new_names(names)
		self.set_nums(nums)

	def auto_number(self, e):
		self.save_for_undo()
		names = self.get_new_names()
		nums = FixerUtils.auto_number(names)
		self.set_nums(nums)

	def cleanup(self, names):
		self.save_for_undo()
		split_by = "_"
		if (self.chk_hyphen.IsChecked()):
			split_by = split_by + "|-"
		if (self.chk_fullstop.IsChecked()):
			split_by = split_by + "|\."
		camelfix = self.chk_camel.IsChecked()
		capsfix = self.chk_all_caps.IsChecked()
		names = self.get_new_names()
		names = FixerUtils.cleanup(names, split_by, camelfix, capsfix)
		self.set_new_names(names)

	def replace(self, e):
		self.save_for_undo()
		find = self.find_str.GetValue()
		repl = self.replace_str.GetValue()
		names = self.get_new_names()
		casens = self.chk_case.GetValue()
		regex = self.chk_regex.GetValue()
		names = FixerUtils.replace(names, find, repl, casens, regex)
		self.set_new_names(names)

	def rename(self, e):
		oldnames = self.get_old_names()
		newnames = self.get_new_names()
		nums = self.get_nums()
		exts = self.get_exts()
		dir = self.get_dir()
		(oldnames, newnames, nums, exts) = FixerUtils.rename_files(oldnames, newnames, nums, exts, dir)
		self.set_old_names(oldnames)
		self.set_new_names(newnames)
		self.set_nums(nums)
		self.set_exts(exts)
	
	def exit(self, e):
		quit()



# Class for drag-drop target

class FixerDropTarget(wx.FileDropTarget):

	def __init__(self, receiver):
		wx.FileDropTarget.__init__(self)
		self.receiver = receiver

	def OnDropFiles(self, x, y, files):
		self.receiver.files_dropped(files)
		return True



# Class for window frame which contains the panel

class FixerFrame(wx.Frame):

	def __init__(self, parent): 
		super(FixerFrame, self).__init__(parent) 
		# set properties
		self.SetSize((1024,600))
		self.SetTitle("Filename Fixer")
		self.panel = FixerPanel(self)
		self.SetBackgroundColour(wx.Colour(220, 220, 220, 255))
		# set up drag-and-drop target
		dtg = FixerDropTarget(self)
		self.SetDropTarget(dtg)
		# let's see it
		self.Show()
		
	def files_dropped(self, files):
		self.panel.populate_from_drop(files)



# Utility class to keep the business logic away from the GUI

class FixerUtils:
	
	# find longest common prefix and suffix for a list of strings
	def find_common(names):
		prefix = names[0].strip().lower()
		suffix = names[0].strip().lower()
		for name in names:
			name = name.strip()
			while (prefix and name[:len(prefix)].lower() != prefix):
				prefix = prefix[:-1]
			while (suffix and name[-len(suffix):].lower() != suffix):
				suffix = suffix[1:]
		return (prefix, suffix)

	# remove specified prefix and suffix, where present, from strings in a list
	def trim_common(names, prefix, suffix):
		fixed = list()
		prefix = prefix.strip().lower()
		suffix = suffix.strip().lower()
		for name in names:
			name = name.strip()
			if (name[:len(prefix)].lower() == prefix):
				name = name[len(prefix):]
			if (name[-len(suffix):].lower() == suffix):
				name = name[:-len(suffix)]
			name = name.strip()
			fixed.append(name)
		return fixed
		
	def trim_iplayer(names):
		return [ re.sub("_[bcdfghj-np-tv-z][0-9bcdfghj-np-tv-z]{7}_(original|technical|editorial|iplayer|shortened|legal|podcast|other)$", "", name) for name in names ]
	
	def trim_youtube(names):
		fixed = list()
		for name in names:
			foo = re.sub("-[a-zA-Z0-9_\-]{11}$", "", name)
			foo = re.sub(" \[[a-zA-Z0-9_\-]{11}\]$", "", foo)
			fixed.append(foo)
		return fixed
		
	def replace(names, old, new, casens, regex):
		fixed = list()
		for name in names:
			if regex:
				if casens:
					fixed.append(re.sub(old, new, name))
				else:
					fixed.append(re.sub(old, new, name, flags = re.I))
			else:
				if casens:
					fixed.append(name.replace(old, new))
				else:
					i = 0
					while (i := name.lower().find(old.lower(), i)) != -1:
						name = name[:i] + new + name[i + len(old):]
						i = i + len(new)
					fixed.append(name)
		return fixed

	def auto_number(names):
		nums = list(map(str, range(1, 1 + len(names))))
		nums = FixerUtils.pad_numbers(nums)
		return nums

	def extract_numbers(names):
		fixed = list()
		nums = list()
		for name in names:
			match = re.search("^([0-9]+[a-zA-Z]*)[ _\-]*", name)
			if (match):
				num = match.group(1)
				span = match.span()
				name = name[0:span[0]] + name[span[1]:]
			else:
				num = ''
			fixed.append(name)
			nums.append(num)
		nums = FixerUtils.pad_numbers(nums)
		return(fixed, nums)

	def pad_numbers(nums):
		fixed = list()
		# break into (digits, suffix) tuples
		nums = list(map(lambda x : re.search("^(\d*)(.*)", x).group(1,2), nums))
		# find largest number
		largest = max(map(lambda x : int('0' + x[0]), nums))
		# see how many digits it has, but pad to at least two
		digits = max(len(str(largest)), 2)
		# smoosh tuples back into strings, padding numeric part as required
		for num in nums:
			if str(num[0]).isnumeric():
				num = str(int(num[0])).zfill(digits) + num[1]
				fixed.append(num)
		return fixed

	def number_by_mod_date(dir, names, exts):
		nums = [''] * len(names)
		tuples = list()
		for i, name in enumerate(names):
			fullname =  dir + name + exts[i]
			mtime = os.path.getmtime(fullname)
			tuples.append( (mtime, i) )
		tuples.sort()
		for i, tuple in enumerate(tuples):
			nums[tuple[1]] = str(i + 1).zfill(3)
		nums = FixerUtils.pad_numbers(nums)
		return(nums)

	def number_by_date_in_filename(names):
		fixed = list()
		nums = [''] * len(names)
		tuples = list()
		for i, name in enumerate(names):
			match = re.search("\(\d{4}-\d\d-\d\d \d\d_\d\d_\d\d\)", name)
			if (match):
				tuples.append( (match.group(0), i) )
				span = match.span()
				name = name[0:span[0]] + name[span[1]:]
			fixed.append(name)
		tuples.sort()
		for i, tuple in enumerate(tuples):
			nums[tuple[1]] = str(i + 1).zfill(3)
		nums = FixerUtils.pad_numbers(nums)
		return(fixed, nums)

	def cleanup(names, split_by, camelfix, capsfix):
		names = [ FixerUtils.fix_spacing(name, split_by, camelfix) for name in names ]
		return [ FixerUtils.fix_capitalisation(name, capsfix) for name in names ]

	def fix_spacing(name, split_by, camelfix):
		# convert punctuation to whitespace
		name = re.sub(split_by, " ", name)
		# fix camel case - do this twice to catch single-letter words that get skipped over the first time
		if (camelfix):
			name = re.sub("[A-Z]", " \g<0>", name)
		# remove unwanted extra spaces
		name = re.sub("\s+", " ", name).strip()
		return name
	
	def fix_capitalisation(name, capsfix):
		all_upper = (name == name.upper()) or capsfix
		words = name.split(" ")
		newwords = list()
		for word in words:
			# if there are any lower-case letters in the name, leave any upper-cased words alone
			word_is_upper = (word == word.upper())
			if all_upper or not word_is_upper or word == 'A':
				word = FixerUtils.title_case(word)
			newwords.append(word)
		words = newwords
		# first word is always capitalised
		words[0] = FixerUtils.upper_first_letter(words[0])
		name = " ".join(words)
		return name

	def title_case(word):
		lcwords = ["a", "an", "in", "the", "and", "or", "of", "is", "to", "with", "as", "for"]
		word = word.lower()
		if (word not in lcwords):
			word = FixerUtils.upper_first_letter(word)
		return word
	
	def upper_first_letter(word):
		match = re.search("[a-zA-Z]", word)
		if (match):
			pos = match.span()[0]
			word = word[0:pos] + word[pos].upper() + word[pos+1:]
		return word
	
	def fix_list_length(list, required_length):
		while len(list) < required_length:
			list.append('')
		return list[:required_length]

	# returns tuple (oldnames, newnames, exts) with successfully renamed files removed
	def rename_files(oldnames, newnames, nums, exts, dir):
		# fix list lengths
		count = len(oldnames)
		if (count != len(newnames)):
			newnames = FixerUtils.fix_list_length(newnames, count)
		if (count != len(nums)):
			nums = FixerUtils.fix_list_length(nums, count)
		# do the renaming, in reverse order so we can del by index
		for i in range(count-1,-1,-1):
			num = nums[i]
			if num:
				num = num + ' - '
			oldname = dir + oldnames[i] + exts[i]
			newname = dir + num + newnames[i] + exts[i].lower()
			if (oldname == newname):
				# if name is unchanged, nothing to do, remove file from lists
				del oldnames[i]
				del newnames[i]
				del nums[i]
				del exts[i]
			else:
				try:
					os.rename(oldname, newname)
				except:
					pass
				else:
					# if rename worked, remove file from lists
					del oldnames[i]
					del newnames[i]
					del nums[i]
					del exts[i]
		return (oldnames, newnames, nums, exts)



# get this party started
app = wx.App()
frame = FixerFrame(None)
app.MainLoop()


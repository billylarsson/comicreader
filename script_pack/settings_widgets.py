from PyQt5           import QtCore, QtGui, QtWidgets
from PyQt5.QtCore    import QPoint, Qt
from bscripts.tricks import tech as t
import os
import time
from script_pack.preset_colors import *



class GOD(QtWidgets.QLabel):
    """
    this is like a template used for many-many widgets
    self.parent, self.main, self.type and t.style(self)
    """
    def __init__(self, place, main=None, type=None, show=True, style=True, extravar=None):
        super(GOD, self).__init__(place)
        self.setLineWidth(0)
        self.setMidLineWidth(0)

        self.fortifyed = False # you can move this around
        self.highlighted = False # shines in gui

        self.set_main_and_place(place, main)
        self.set_type(place, type)
        self.set_extra_variables(extravar)
        self.set_styling(style)

        if show:
            self.show()

    def special(self):
        return False

    def set_styling(self, style):
        if style and 'type' in dir(self):
            t.style(self)

    def set_type(self, place, type):
        if type:
            self.type = type
        elif 'type' in dir(place):
            self.type = place.type

    def set_main_and_place(self, place, main):
        self.parent = place

        if main:
            self.main = main
        elif place:
            self.main = place

    def set_extra_variables(self, extravar):

        if extravar and type(extravar) == dict:

            keys = list(extravar.keys())
            values = list(extravar.values())

            for count in range(len(keys)):
                setattr(self, keys[count], values[count])

    def change_button_color(self, active, background=None, darkred=False):
        if 'button' in dir(self):
            if background:
                t.style(self.button, background=background)

            elif not self.special():
                if active:
                    t.style(self.button, background=BTN_ON)
                else:
                    if darkred:
                        t.style(self.button, background=DARKRED)
                    else:
                        t.style(self.button, background=BTN_OFF)

    def activation_toggle(self, force=None, save=True, background=None, toggle=True, gui=True, signal=True):

        if force != None:
            self.activated = force

        elif 'activated' not in dir(self):
            self.activated = t.config(self.type)

        elif self.activated and toggle:
            self.activated = False

        elif not self.activated and toggle:
            self.activated = True

        if gui:
            self.change_button_color(self.activated, background=background)

        if save and 'type' in dir(self):
            t.save_config(self.type, self.activated)

        if signal and 'type' in dir(self):
            signal = t.signals(self.type)
            signal.activated.emit(self.activated is bool)

        return self.activated

    def highlight_toggle(self, force=None, toggle=True, background=None, gui=True):
        if force != None:
            self.highlighted = force

        elif toggle:

            if self.highlighted:
                self.highlighted = False
            else:
                self.highlighted = True

        else:
            return self.highlighted

        if gui:
            self.change_button_color(self.highlighted, background=background)

class CheckableWidget(GOD):
    """
    a QLineEdit with some text that sits next to a QLabel that immitatates a and
    looks like a QPushButtons who changes from red to green when clicking on it.
    the text is always normalized to fit the label, to enforce a certain fontsize
    dict(textsize=dict(maxsize=INT, minsize=INT))

    :param dictionary
        text = the in the QLineEdit
        dict(textsize=
                maxsize = int, maximum font size
                minsize = int, minmum font size
        button_text = text
        button_text_color = rgb
        button_color = rgb
        text_color = rgb
        text_background = QLineEdits background color
        button_width_factor = 1 is a square, larger factor makes a wider button
        button_linewidth = int

    """
    def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
        if ev.button() == 1:
            self.activation_toggle()

    def default_event_colors(self):
        self.directives['activation'] = [
            dict(object=self.textlabel, color='white'),
            dict(object=self.button, background=BTN_SHINE_GREEN, color=BTN_SHINE_GREEN),
        ]

        self.directives['deactivation'] = [
            dict(object=self.textlabel, color=BTN_SHADE),
            dict(object=self.button, background=BTN_SHADE, color=BTN_SHADE),
        ]

    def fill_dictionary_defaults(self, dictionary):
        """
        default values are put into the dictionary if not earlier specified
        :param dictionary:
        """
        if 'button_text' not in dictionary:
            dictionary['button_text'] = ''

        if 'button_text_color' not in dictionary:
            dictionary['button_text_color'] = 'white'

        if 'button_color' not in dictionary:
            dictionary['button_color'] = 'gray'

        if 'text_color' not in dictionary:
            dictionary['text_color'] = 'white'

        if 'text_background' not in dictionary:
            dictionary['text_background'] = 'black'

        if 'button_width_factor' not in dictionary:
            dictionary['button_width_factor'] = 1

        if 'alignment' in dictionary:
            if dictionary['alignment'] == True:
                dictionary['alignment'] = QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter
        else:
            dictionary['alignment'] = False

        if 'shrink_to_text' not in dictionary:
            dictionary['shrink_to_text'] = False

        if 'button_linewidth' not in dictionary:
            dictionary['button_linewidth'] = self.parent.lineWidth() - 1
            if dictionary['button_linewidth'] < 2:
                dictionary['button_linewidth'] = 2

        if 'textsize' in dictionary:
            dictionary['maxsize'] = dictionary['textsize']
            dictionary['minsize'] = dictionary['textsize'] - 1
        else:
            if 'maxsize' not in dictionary:
                dictionary['maxsize'] = 24

            if 'minsize' not in dictionary:
                dictionary['minsize'] = 5

    def draw_checkable_widget(self, dictionary):
        """
        this is adding the red/green button and textlabel textlabel
        onto the widget itself from a parents loop (dictionary)
        :param dictionary: comes from parent
        """
        self.fill_dictionary_defaults(dictionary)

        def set_alignment(self, alignment):
            if alignment:
                self.textlabel.setAlignment(alignment)

        def shrink_expand_or_keep(self, shrink_to_text):
            if shrink_to_text:
                w = self.textlabel.fontMetrics().boundingRect(self.textlabel.text()).width()
                width_change = self.textlabel.width() - w

                if type(shrink_to_text) == dict and 'margin' in shrink_to_text:
                    width_change -= shrink_to_text['margin'] * 2
                else:
                    width_change -= 2+2

                if width_change > 1:
                    canvas = dictionary['settingscanvas']
                    for i in [canvas, self, self.textlabel]:
                        t.pos(i, width=i.width() - width_change)


        # >>======================= [ BELOW ] }>============BELOW:ME========>>
        maxsize = dictionary['maxsize']
        minsize = dictionary['minsize']

        button_text = dictionary['button_text']
        button_color = dictionary['button_color']
        button_text_color = dictionary['button_text_color']

        text = ' ' + dictionary['text']
        text_color = dictionary['text_color']
        text_background = dictionary['text_background']

        button_width_factor = dictionary['button_width_factor']
        button_linewidth = dictionary['button_linewidth']

        alignment = dictionary['alignment']
        shrink_to_text = dictionary['shrink_to_text']
        # <<======ABOVE:ME=======<{ [ABOVE] ==============================<<
        t.style(self, background='rgba(0,0,0,0)')

        self._bframe = t.pos(new=self, inside=self, width=self.height() * button_width_factor, background='black')

        self.button = t.pos(new=self, inside=self._bframe, margin=button_linewidth)
        self.button.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)

        self.textlabel = t.pos(new=self, inside=self, after=self._bframe, x_margin=button_linewidth-1)
        t.pos(self.textlabel, left=self.textlabel, right=self)

        d = {
            self.textlabel: dict(text=text, text_background=text_background, text_color=text_color),
            self.button: dict(text=button_text, text_background=button_color, text_color=button_text_color)
        }

        for k,v in d.items():
            k.setText(v['text'])
            t.style(k, background=v['text_background'], color=v['text_color'])
            t.correct_broken_font_size(k, maxsize=maxsize, minsize=minsize)

        set_alignment(self, alignment)
        shrink_expand_or_keep(self, shrink_to_text)

        dictionary.update(button=self.button, textlabel=self.textlabel)

        self.activation_toggle(toggle=False, save=False)

class ExecutableLookCheckable(CheckableWidget):
    """
    an executable button that has a progress bar built inside it self
    signals makes the progress bar go larger in size and tooltip can
    show the exact progress level
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.running_job = False

    def show_progress(self, progress):
        """
        :param progress: dict-keys(start, total, current, last_emit)
        """
        def set_tooltip():
            started = round(time.time() - progress['start'])
            percent = round(1 - (progress['current'] / progress['total'] * 100), 2)
            percent = percent - percent - percent # turns out positive
            tooltip = f"Job started {started}s ago and has processed {progress['current']} of {progress['total']} (approximately: {percent}% done so far)"
            self.tmp_label.setToolTip(tooltip)

        progress['last_emit'] = time.time()
        hundred = self.button.width()
        current = self.progress_label.width()
        newprog = hundred * (progress['current'] / progress['total'])
        if newprog > current:
            t.pos(self.progress_label, width=newprog)
            t.correct_broken_font_size(self.progress_label, x_margin=3)

        set_tooltip()
        if not self.running_job:
            progress['stop'] = True

    def jobs_done(self, finished_text='DONE!', finished_color=JOB_SUCCESS, slave_can_alter=True, running_job=False):
        """
        kills the progress bar (labels) and prints out DONE on the primary label
        """
        t.signals(self.progress_signal.name, delete=True)
        t.style(self.button, background=finished_color)
        self.button.setText(finished_text)
        t.correct_broken_font_size(self.button, x_margin=3)
        self.progress_label.close()
        self.tmp_label.close()
        self.running_job = running_job
        self.slaves_can_alter = slave_can_alter

    def job_stopped(self, progress=None, *args, **kwargs):
        self.jobs_done(finished_text='STOPPED!', finished_color=JOB_STOPPED, *args, **kwargs)

    def job_error(self, progress=None, *args, **kwargs):
        self.jobs_done(finished_text='ERROR!', finished_color=JOB_ERROR, *args, **kwargs)

    def start_job(self, signalgroup, default_progress=True, default_finished=True, default_stop=True, default_error=True):

        def create_progress_label_and_button(self):
            self.progress_label = t.pos(new=self.button, inside=self.button, background='darkGreen', width=1)
            self.tmp_label = t.pos(new=self.button, inside=self.button)
            self.tmp_label.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
            self.tmp_label.setText('RUNNING')
            t.style(self.tmp_label, background='rgba(5,5,5,5)', color='black')
            t.correct_broken_font_size(self.tmp_label, x_margin=3, y_margin=0)

        self.slaves_can_alter = False
        self.running_job = True

        self.progress_signal = t.signals(signalgroup)
        self.progress_signal.name = signalgroup

        t.style(self.button, background='darkGray')
        self.button.setText("")

        create_progress_label_and_button(self)

        if default_progress:
            self.progress_signal.progress.connect(self.show_progress)

        if default_finished:
            self.progress_signal.finished.connect(self.jobs_done)

        if default_stop:
            self.progress_signal.stop.connect(self.job_stopped)

        if default_error:
            self.progress_signal.error.connect(self.job_stopped)

class GLOBALDeactivate(GOD):
    """
    global highlighting on mousehover for the entire program
    this has no clickable event and only reacts on mouse movement.
    """
    def __init__(self, place, global_signal=None, *args, **kwargs):
        super().__init__(place, *args, **kwargs)
        self.setMouseTracking(True)
        self.global_deactivation_signal = t.signals(global_signal or 'global_on_off_signal')
        self.global_deactivation_signal.deactivate.connect(self.signal_global_deactivate)
        self.global_deactivation_signal.activate.connect(self.signal_global_activate)
        self.directives = dict(activation=[], deactivation=[]) # special values inside here
        self.slaves_can_alter = True

    def change_color_on_mousehover(self, ev):
        """
        emits activate/deactivate whereever the mouse is inside or outside its area
        """
        if ev.pos().x() < 3 or ev.pos().x() > self.width() - 3:
            if self.highlighted:
                self.global_deactivation_signal.deactivate.emit(self.type)

        elif ev.pos().y() < 3 or ev.pos().y() > self.height() - 3:
            if self.highlighted:
                self.global_deactivation_signal.deactivate.emit(self.type)

        else:
            if not self.highlighted:
                self.global_deactivation_signal.activate.emit(self.type)

    def signal_global_activate(self, signal):
        """
        if i'm the signal and i'm not yet highlighed, then highlight me!
        :param signal: string
        """
        if self.type != signal:
            return

        if self.highlighted:
            return

        self.highlight_toggle(force=True, gui=False)
        self.signal_global_gui_change(directive='activation', background='black', color='white')

    def signal_global_deactivate(self, signal):
        """
        if i'm NOT the signal and i'm highlighted, i'm turned off!
        :param signal: string
        """
        if self.type == signal:
            return

        if not self.highlighted:
            return

        if not self.slaves_can_alter:
            return

        self.highlight_toggle(force=False, gui=False)
        self.signal_global_gui_change(directive='deactivation', background='black', color='gray')

    def signal_global_gui_change(self, directive, background=None, color=None):
        """
        this can be highjacked directly to alter appearance
        :param directive: activation or deactivation (should've been a bool)
        :param background: rgb
        :param color: rgb
        """
        if type(self.directives[directive]) == dict:
            user_sets = [self.directives[directive]]
        else:
            user_sets = self.directives[directive]
            if not user_sets:
                user_sets.append({})

        for gui_settings in user_sets:
            d = dict(object=self, background=background, color=color)
            for k,v in d.items():
                if k in gui_settings:
                    d[k] = gui_settings[k]

            t.style(d['object'], background=d['background'], color=d['color'])

    def mouseMoveEvent(self, ev: QtGui.QMouseEvent) -> None:
        self.change_color_on_mousehover(ev)
        self.global_deactivation_signal.deactivate.emit(self.type)

class CheckBoxSignalGroup(CheckableWidget):
    """
    CLICKING ONLY TURNS ON, theres no toggling

    clicking one box sends signal to all from the same group and the only
    one thats turned on is the clicked one and all others are turned off
    """
    def __init__(self, place, signalgroup=None,  *args, **kwargs):
        super().__init__(place, *args, **kwargs)

        self.signalgroup = t.signals(signalgroup)
        self.signalgroup.checkgroup_master.connect(self.checkgroup_signal)

    def checkgroup_signal(self, signal):
        """
        everyone gets the signal, if i'm on and not the signal i turn off and vice versa
        :param signal: string
        """

        if self.activated and self.type != signal:
            self.activation_toggle(force=False)

        elif not self.activated and self.type == signal:
            self.activation_toggle(force=True)

    def fall_back_to_default(self, list_with_widgets, fallback_type):
        """
        when we iter all widgets and none of these are active
        accodring to settings, then we activate to fallback_type
        :param list_with_widgets:
        :param fallback_type: string
        """
        for count, i in enumerate(list_with_widgets):

            if t.config(i.type):
                i.signalgroup.checkgroup_master.emit(i.type)
                break

            elif count+1 == len(list_with_widgets): # falls back to default
                i.signalgroup.checkgroup_master.emit(fallback_type)

    def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
        if ev.button() == 1:
            self.signalgroup.checkgroup_master.emit(self.type)

class HighlightRadioBoxGroup(CheckBoxSignalGroup, GLOBALDeactivate):
    """
    this is a combination group that both highlights niceley and toggles from its inheritance

    requirements:

    self.post_init()
    self.button
    self.textlabel
    """
    def __init__(self, place, signalgroup=None, *args, **kwargs):
        super().__init__(place=place, signalgroup=signalgroup, *args, **kwargs)
        self.signalgroup_radio_name = signalgroup or 'global_on_off_signal' + '_radio_change'

    def fall_back_to_default(self, list_with_widgets, fallback_type):
        """
        this is not the same as fn: CheckableWithSignal, this will emit two signals
        :param list_with_widgets: all widgets from dict['label'] ...
        :param fallback_type: string
        """
        for count, i in enumerate(list_with_widgets):

            if t.config(i.type):
                i.signalgroup.checkgroup_master.emit(i.type)
                self.enslave_me_signal.deactivate.emit(i.type)
                break

            elif count+1 == len(list_with_widgets): # falls back to default
                i.signalgroup.checkgroup_master.emit(fallback_type)
                self.enslave_me_signal.deactivate.emit(fallback_type)

    def special(self):
        if not self.highlighted:
            t.style(self.button, background='gray')
            t.style(self.textlabel, color='gray')
        else:
            t.style(self.button, background='green')
            t.style(self.textlabel, color='white')

        return True

    def slave_can_alter_signal(self, signal):
        if signal == self.type:
            self.slaves_can_alter = False
            self.highlight_toggle(force=True)
            
            if not t.config(self.type):
                t.save_config(self.type, True)

        else:
            self.slaves_can_alter = True
            self.highlight_toggle(force=False)

            if t.config(self.type):
                t.save_config(self.type, False)

    def post_init(self):
        self.button.setMouseTracking(True)
        self.textlabel.setMouseTracking(True)
        self.enslave_me_signal = t.signals(self.signalgroup_radio_name)
        self.enslave_me_signal.deactivate.connect(self.slave_can_alter_signal)
        self.default_event_colors()

    def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
        if ev.button() == 1:
            self.enslave_me_signal.deactivate.emit(self.type)

class CheckableAndGlobalHighlight(CheckableWidget, GLOBALDeactivate):
    """
    this is kind of a hack, gives checkable widgets the ability
    to mouse hover highlight its not bad so i may keep up with it
    """
    def post_init(self):
        self.button.setMouseTracking(True)
        self.textlabel.setMouseTracking(True)
        self.default_event_colors()

    def signal_global_deactivate(self, signal):
        """
        if i'm NOT the signal and i'm highlighted, i'm turned off
        unless i'm activated, then i'm showing my on-colors
        :param signal: string
        """
        if self.type == signal:
            return

        if not self.highlighted:
            return

        if not self.slaves_can_alter:
            return

        self.highlight_toggle(force=False, gui=False)

        if self.activated:
            self.activation_toggle(toggle=False, save=False) # not ugly, but its a hack -> gui change only
        else:
            self.signal_global_gui_change(directive='deactivation', background='black', color='gray')



class LCD(QtWidgets.QLCDNumber):
    def __init__(self, place, digitmultiplyer, type, clickable=True, autosave=True, background='black', color='white'):
        """
        :param digitmultiplyer: 1, 10, 100, 1000...
        how much to multiply its value with when saving to config
        """
        super().__init__(place)
        self.type = type
        self.parent = place
        self.autosave = autosave
        self.clickable = clickable
        self.multiplyer = digitmultiplyer
        t.style(self, background=background, color=color)

    def get_current_value(self):
        total = 0
        for i in self.all_lcd:
            total += i.value() * i.multiplyer

        return total

    def set_new_value(self, change=0, direct_value=0):
        """
        inside each LCD part all LCD-widgets are accessable in self.all_lcd
        so pressing one gathers all values from all LCD-widgets an combines
        their value, saving to config and displaying correct amount
        :param change: positive or negative int
        :param direct_value: set this value
        """
        if change:
            total = self.get_current_value()
            total += change

        else:
            total = direct_value

        if total > self.parent.max_value:
            total = self.parent.max_value
        elif total < self.parent.min_value:
            total = self.parent.min_value

        for count, i in enumerate(self.all_lcd):
            CountLabel.get_and_display_lcd_value(i, count, len(self.all_lcd), total_value=int(total))

        if self.autosave:
            t.save_config(self.type, int(total))

    def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
        if not self.clickable:
            return

        elif ev.button() == 1:
            self.set_new_value(change= +1 * self.multiplyer) # addition
        elif ev.button() == 2:
            self.set_new_value(change= -1 * self.multiplyer) # subraction

class CountLabel(GOD):
    def make_title_label(self, text="", tooltip="", background='black', color='white', font='14pt'):
        """
        makes the label that shows title and tooltip
        :param text, tooltip
        """
        self.title_label = QtWidgets.QLabel(self)
        self.title_label.show()
        self.title_label.setText(text)
        self.title_label.setToolTip(tooltip)
        t.style(self.title_label, background=background, color=color, font=font)
        width = self.title_label.fontMetrics().boundingRect(self.title_label.text()).width()
        t.pos(self.title_label, height=self, width=width)

    def extend_title_to_reach_lcd(self):
        """
        always assumes that the far left LCD got into the list last
        """
        if not 'title_label' in dir(self) or 'lcd_displays' not in dir(self):
            return

        t.pos(self.title_label, left=self.title_label, right=self.lcd_displays[-1].geometry().left())
        self.expand_to_lest_size()

    def move_lcds_next_to_title(self, margin=5):
        """
        always assumes that the far left LCD got into the list last
        adds a margin between title and preceeding LCD
        """
        if not 'title_label' in dir(self) or 'lcd_displays' not in dir(self):
            return

        for count in range(len(self.lcd_displays)-1,-1,-1):
            lcd = self.lcd_displays[count]

            if count+1 == len(self.lcd_displays):
                t.pos(lcd, after=self.title_label)
                t.pos(lcd, move=[margin,0])
                self.extend_title_to_reach_lcd()
            else:
                t.pos(lcd, after=self.lcd_displays[count+1])

        self.expand_to_lest_size()

    def expand_to_lest_size(self):
        if self.width() < self.lcd_displays[0].geometry().right():
            t.pos(self, width=self.lcd_displays[0].geometry().right())

    @staticmethod
    def get_and_display_lcd_value(lcd_widget, lcd_position, lcds_in_this_row, total_value=None):
        """
        gets one lcd_widget and its current position among how
        many, gets the total value for all lcd_widgets from
        global settings and sets only its value
        :param lcd_widget: QLCDdisplay
        :param total: int how many LCD Displays in the same row
        :param lcd_position: its current position among all LCDs
        :param total_value: the value all LCD together creates
        """
        def total_value_checker(total_value):
            if total_value and total_value < 1:
                total_value = 1
            return total_value

        if not total_value and 'type' in dir(lcd_widget): # gets total value if not provided
            total_value = t.config(lcd_widget.type) or 0

        total_value = total_value_checker(total_value) or 0

        lcd_widget.setDigitCount(1)
        total_value = t.zero_prefiller(total_value, lcds_in_this_row)
        total_value = list(total_value)
        total_value.reverse()
        lcd_widget.display(int(total_value[lcd_position]))

    def genereate_multiplyerlist(self, lcds_in_this_row):
        """ returns {0:1, 1:10, 2:100} ... """
        cycle = [1]
        for count in range(1, lcds_in_this_row):
            cycle.append(cycle[-1] * 10)
        return cycle

    def correct_to_small_geometry(self, lcd_displays):
        least_size = 0

        for i in lcd_displays:
            least_size += i.width()

        if least_size > self.width():
            extra = least_size - self.width()
            t.pos(self, width=least_size)

            for i in lcd_displays:
                t.pos(i, move=[extra,0])


    def draw_lcd_widget(self,
                        type,
                        lcds_in_this_row=3,
                        clickable=True,
                        autosave=True,
                        background='black',
                        color='white',
                        max_value=999,
                        min_value=0
                        ):
        """
        adds three LCD widgets aside each others that each handles 1, 10, 100s
        this is suboptimal solution that did give some ease on the parents fn
        """
        self.max_value = max_value
        self.min_value = min_value

        cycle = self.genereate_multiplyerlist(lcds_in_this_row)
        self.lcd_displays = []

        for count, multi in enumerate(cycle):
            lcd = LCD(self, multi, type=type, clickable=clickable, autosave=autosave, background=background, color=color)
            self.get_and_display_lcd_value(lcd, lcd_position=count, lcds_in_this_row=lcds_in_this_row)

            if count == 0:
                self.set_new_value = lcd.set_new_value
                self.get_current_value = lcd.get_current_value
                w = self.height() * 0.4
                t.pos(lcd, height=self, width=w, right=self)
            else:
                prevlcd = self.lcd_displays[-1]
                t.pos(lcd, coat=prevlcd, right=prevlcd.geometry().left())

            self.lcd_displays.append(lcd)
            lcd.show()

        self.spread_all_lcds_among_all_lcds(self.lcd_displays)
        self.correct_to_small_geometry(self.lcd_displays)
        return self.lcd_displays

    def spread_all_lcds_among_all_lcds(self, list_with_all_lcds):
        """
        this is so that when you save-to-config while clicking
        one of those the total number can be accessed
        """
        for lcd in list_with_all_lcds:
            lcd.all_lcd = list_with_all_lcds

class CheckableLCD(CountLabel, CheckableWidget):
    pass

class LCDRow(CountLabel):
    def __init__(self, place, lcds_in_this_row=3, type=None, clickable=True, autosave=True, height=None, background='black', color='white'):
        super(LCDRow, self).__init__(place)
        self.clickable = clickable
        self.autosave = autosave
        self.set_height(height)
        self.draw_lcd_widget(type, lcds_in_this_row=lcds_in_this_row, clickable=clickable, autosave=autosave, background=background, color=color)
        self.show()

    def set_height(self, height):
        if height:
            t.pos(self, height=height)
        else:
            t.pos(self, height=self.parent)


class FolderSettingsWidget(CheckableWidget):
    def __init__(self, place, multiple_folders=True, *args, **kwargs):
        super().__init__(place=place, *args, **kwargs)
        self.multiple_folders = multiple_folders

    def post_init(self):
        self.dir_pixel = []
        self.lineedit.textChanged.connect(self.text_changed)
        rv = t.config(self.type, curious=True)

        if rv and type(rv) == list:
            self.create_small_folder_pixles(path=rv[0])
            loc = t.separate_file_from_folder(rv[0])
            self.lineedit.setText(loc.full_path)

        elif rv:
            self.activation_toggle(force=True, save=False)

        else:
            self.activation_toggle(force=False, save=False)

    class ManageButton(HighlightRadioBoxGroup):
        def __init__(self, place, parent, text, *args, **kwargs):
            super().__init__(place, *args, **kwargs)
            self.parent = parent
            self.setText(text)
            self.setFrameShape(QtWidgets.QFrame.Box)
            self.setLineWidth(place.lineWidth())
            self.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)

            self.post_init()

            self.highlight_toggle(force=False)

            t.style(self,
                    background=self.directives['deactivation'][0]['background'],
                    color=self.directives['deactivation'][0]['color'])


    def manage_save_button(self, create=False, delete=False, make_small=False, text='SAVE'):

        def reuse_or_destroy(self, create, delete):
            if 'save_button' in dir(self) and create:
                return True

            elif delete:
                if 'save_button' in dir(self) and delete:
                    right = self.lineedit.geometry().right()
                    t.pos(self.lineedit, left=self.save_button, right=right)
                    self.save_button.close()
                    del self.save_button
                return True

        if reuse_or_destroy(self, create, delete):
            return

        class SaveButton(self.ManageButton):

            def post_init(self):
                self.enslave_me_signal = t.signals(self.signalgroup_radio_name)
                self.enslave_me_signal.deactivate.connect(self.slave_can_alter_signal)

                self.directives['activation'] = [
                    dict(object=self, background='rgb(250, 195, 0)', color='black'),
                ]

                self.directives['deactivation'] = [
                    dict(object=self, background='rgb(180, 135, 0)', color='black'),
                ]

            def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
                if ev.button() == 1:
                    text = self.parent.lineedit.text().strip()

                    for i in self.parent.dir_pixel:
                        if i.activated:
                            self.parent.save_or_delete_this_location(exclude_location=i.path, refresh=False)
                            break

                    self.parent.save_or_delete_this_location(include_location=text)

        signal = self.global_deactivation_signal.name
        linewidth = self.parent.lineWidth() or 1
        self.save_button = SaveButton(
            self.parent, type='_save_button' + self.type, text=text, parent=self, global_signal=signal)
        t.pos(self.save_button, coat=self.lineedit, left=self.lineedit, width=60 - linewidth)
        t.pos(self.lineedit, move=[60,0], width=self.lineedit, add=-60)
        t.correct_broken_font_size(self.save_button, x_margin=2, y_margin=0)

        if make_small:
            t.pos(self.save_button, height=self.height() * 0.5)

    def manage_extend_button(self, create=False, delete=False, text='APPEND'):

        def reuse_or_destroy(self, create, delete):
            if 'extend_button' in dir(self) and create:
                return True

            elif delete:
                if 'extend_button' in dir(self) and delete:
                    right = self.lineedit.geometry().right()
                    t.pos(self.lineedit, left=self.extend_button, right=right)
                    self.extend_button.close()
                    del self.extend_button
                return True

        class ExtendButton(self.ManageButton):

            def post_init(self):
                self.enslave_me_signal = t.signals(self.signalgroup_radio_name)
                self.enslave_me_signal.deactivate.connect(self.slave_can_alter_signal)

                self.directives['activation'] = [
                    dict(object=self, background='rgb(250, 195, 0)', color='black'),
                ]

                self.directives['deactivation'] = [
                    dict(object=self, background='rgb(180, 135, 0)', color='black'),
                ]

            def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
                if ev.button() == 1:
                    text = self.parent.lineedit.text().strip()
                    self.parent.save_or_delete_this_location(include_location=text)

        if reuse_or_destroy(self, create, delete):
            return

        signal = self.global_deactivation_signal.name
        self.extend_button = ExtendButton(
            self.parent, type='_extend_button' + self.type, text=text, parent=self, global_signal=signal)
        t.pos(self.extend_button, coat=self.save_button, below=self.save_button)
        t.correct_broken_font_size(self.extend_button, x_margin=2, y_margin=0)


    def manage_delete_button(self, create=False, delete=False, text='DELETE'):
        def reuse_or_destroy(self, create, delete):
            if 'delete_button' in dir(self) and create:
                return True

            elif delete:
                if 'delete_button' in dir(self) and delete:
                    right = self.lineedit.geometry().right()
                    t.pos(self.lineedit, left=self.delete_button, right=right)
                    self.delete_button.close()
                    del self.delete_button
                return True

        class DeleteButton(self.ManageButton):
            def post_init(self):
                self.enslave_me_signal = t.signals(self.signalgroup_radio_name)
                self.enslave_me_signal.deactivate.connect(self.slave_can_alter_signal)

                self.directives['activation'] = [
                    dict(object=self, background='rgb(250, 10, 10)', color='black')]

                self.directives['deactivation'] = [
                    dict(object=self, background='rgb(115, 10, 10)', color='black')]

            def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
                if ev.button() == 1:
                    text = self.parent.lineedit.text().strip()
                    self.parent.save_or_delete_this_location(exclude_location=text)

        def make_delete_button(self):
            signal = self.global_deactivation_signal.name

            linewidth = self.parent.lineWidth() or 1
            w = int(self.height() * 0.3) + linewidth
            le_right = self.lineedit.geometry().right()
            self.delete_button = DeleteButton(
                self.parent, type='_delete_button' + self.type, text=text, parent=self, global_signal=signal)

            t.pos(self.delete_button, coat=self.lineedit, left=self.lineedit, width=w)
            t.pos(self.lineedit, left=dict(right=self.delete_button), x_margin=linewidth)
            t.pos(self.lineedit, left=self.lineedit, right=le_right)
            self.delete_button.setToolTip('DELETE THIS PATH FROM SETTINGS')

        if reuse_or_destroy(self, create, delete):
            return

        make_delete_button(self)

    def text_changed(self):
        if self.text_path_exists() and not self.text_in_database():
            t.style(self.lineedit, background='black', color='gray')
            self.manage_delete_button(delete=True)

            if t.config(self.type, curious=True) and self.multiple_folders:
                self.manage_save_button(create=True, text='REPLACE', make_small=True)
                self.manage_extend_button(create=True, text='APPEND')
            else:
                self.manage_save_button(create=True, text='SAVE!?')

        elif self.text_in_database():
            t.style(self.lineedit, background='black', color='white')
            self.manage_save_button(delete=True)
            self.manage_extend_button(delete=True)
            self.manage_delete_button(create=True, text='')

        else:
            self.manage_save_button(delete=True)
            self.manage_extend_button(delete=True)
            self.manage_delete_button(delete=True)
            t.style(self.lineedit, background='black', color='gray')

    def text_path_exists(self):
        text = self.lineedit.text().strip()
        if text and os.path.exists(text):
            return True
        else:
            return False

    def text_in_database(self):
        rv = t.config(self.type, curious=True)
        text = self.lineedit.text().strip()
        if rv and type(rv) == list and text:
            loc1 = t.separate_file_from_folder(text)
            for i in rv:
                loc2 = t.separate_file_from_folder(i)
                if loc1.full_path == loc2.full_path:
                    return True
        return False

    def create_small_folder_pixles(self, path=None):

        class PIX(GOD):
            def __init__(self, place, dir_pixel, type):
                super().__init__(place, type=type)
                self.button = self
                self.dir_pixel = dir_pixel
                self.show()

            def toggle_pixel(self):
                for i in self.dir_pixel:
                    if i == self:
                        i.activation_toggle(force=True, background='green')
                    else:
                        i.activation_toggle(force=False, background='orange')

            def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
                self.toggle_pixel()
                self.le.setText(self.path)

        def close_previous_pix(self):
            for c in range(len(self.dir_pixel)-1,-1,-1):
                self.dir_pixel[c].close()
                self.dir_pixel.pop(c)

        def make_pix(self, list_with_paths):
            for count, store_path in enumerate(list_with_paths):

                loc = t.separate_file_from_folder(store_path)

                pix = PIX(self.parent, self.dir_pixel, type='_pix_' + self.type)
                pix.path = loc.full_path
                pix.le = self.lineedit

                if count == 0:
                    t.pos(pix, coat=self.lineedit, size=[8, 8], right=self.lineedit, move=[-2, 2])
                else:
                    t.pos(pix, coat=self.dir_pixel[-1], before=self.dir_pixel[-1], x_margin=2)

                self.dir_pixel.append(pix)

                if count == 0 and not path:
                    pix.activation_toggle(force=True, background='green')
                elif path and path == loc.full_path:
                    pix.activation_toggle(force=True, background='green')
                else:
                    pix.activation_toggle(force=False, background='orange')

        close_previous_pix(self)
        rv = t.config(self.type, curious=True)

        if not rv or type(rv) != list:
            return

        make_pix(self, list_with_paths=rv)

    def save_or_delete_this_location(self, include_location=None, exclude_location=None, refresh=True):
        """
        include or exclude a location from settings (pop or append to list)
        gui/pix will be updated automatically from here
        :param include_location: string
        :param exclude_location: string
        """
        save = []
        rv = t.config(self.type)
        if type(rv) != list:
            rv = []

        if include_location:
            if self.type == 'cache_folder':  # todo this is to quick and dirty, cache must be single folder
                save = [include_location]
                rv = []
            else:
                rv.append(include_location)

        for i in rv:
            loc = t.separate_file_from_folder(i)
            if loc.full_path not in save and loc.full_path != exclude_location:
                save.append(loc.full_path)

        if save:
            t.save_config(self.type, save)
        else:
            t.save_config(self.type, None, delete=True)

        if refresh:
            self.text_changed() # updates gui
            self.create_small_folder_pixles(path=self.lineedit.text().strip()) # new pix

    def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
        if ev.button() == 1:
            if t.config(self.type, curious=True):
                self.activation_toggle(force=True)
            else:
                self.activation_toggle(force=False)

class FolderSettingsAndGLobalHighlight(FolderSettingsWidget, CheckableAndGlobalHighlight):
    def post_init(self):

        self.button.setMouseTracking(True)
        self.textlabel.setMouseTracking(True)

        self.directives['activation'] = [
            dict(object=self.textlabel, color='white'),
            dict(object=self.button, background='lightGreen', color='lightGreen'),
        ]

        self.directives['deactivation'] = [
            dict(object=self.textlabel, color='gray'),
            dict(object=self.button, background='gray', color='gray'),
        ]

        self.dir_pixel = []
        self.lineedit.textChanged.connect(self.text_changed)
        rv = t.config(self.type, curious=True)

        if rv and type(rv) == list:
            self.create_small_folder_pixles(path=rv[0])
            loc = t.separate_file_from_folder(rv[0])
            self.lineedit.setText(loc.full_path)

        elif rv:
            self.activation_toggle(force=True, save=False)

        else:
            self.activation_toggle(force=False, save=False)

class UniversalSettingsArea(GOD):
    def __init__(self, place, activation_toggle=None, extravar=None, *args, **kwargs):
        super().__init__(place, extravar=extravar, *args, **kwargs)
        self.muted_while_moving = True

        if activation_toggle:
            self.activation_toggle = activation_toggle

        self.set_color_theme(extravar)

    def make_header(self, title, width=100, height=20, background='black', color='gray', text_color='gray', linewidth=1):
        header = t.pos(new=self, width=width, height=height)
        t.style(header, background=background, color=color)
        header.setFrameShape(QtWidgets.QFrame.Box)
        header.setLineWidth(linewidth)
        header.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
        header.setText(title)
        textsize = t.correct_broken_font_size(header, maxsize=80, y_margin=1, x_margin=4)
        header.setText("")
        l = t.pos(new=header, coat=header, margin=linewidth)
        l.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
        t.style(l, background=background, color=text_color, font=str(textsize) + 'pt')
        l.setText(title)
        header.textlabel = l

        return header

    def set_color_theme(self, extravar):
        t.style(self, background='transparent')

        if not extravar or not 'holding' in extravar:
            self.holding = dict(background='rgba(10,10,10,235)', color='rgba(150,150,150,220)')
        if not extravar or not 'releasing' in extravar:
            self.releasing = dict(background='gray', color='black')

    def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
        if ev.button() == 1:
            self.old_position = ev.globalPos()
        elif ev.button() == 2:
            self.activation_toggle(force=False)
            self.close()

    def change_widget_colors_when_something(self, releasing=False, holding=False):
        if self.muted_while_moving:
            return

        if 'blackgrays' not in dir(self):
            return

        for i in self.blackgrays:
            if holding:
                t.style(i, background=self.holding['background'], color=self.holding['color'])
            elif releasing:
                t.style(i, background=self.releasing['background'], color=self.releasing['color'])

    def mouseReleaseEvent(self, ev: QtGui.QMouseEvent) -> None:
        if 'old_position' in dir(self):
            del self.old_position

        self.change_widget_colors_when_something(releasing=True)

    def mouseMoveEvent(self, event):
        if event.button() == 2:
            return

        if 'old_position' not in dir(self):
            return

        if self.fortifyed:
            return

        delta = QPoint(event.globalPos() - self.old_position)
        self.move(self.x() + delta.x(), self.y() + delta.y())
        self.old_position = event.globalPos()
        self.change_widget_colors_when_something(holding=True)

    def expand_me(self, objectlist, add=0):
        """
        expands the backplate to suit the size of all the widgets it is containing
        :param me: usually a self
        :param objectlist: list with all objects placed inside me (self)
        :param add: extra margin
        """
        if type(objectlist) != list:
            objectlist = [objectlist]

        x = 0
        y = 0

        for i in objectlist:
            if x < i.geometry().right() + add:
                x = i.geometry().right() + add

            if y < i.geometry().bottom() + add:
                y = i.geometry().bottom() + add

        t.pos(self, width=x+2, height=y+2)

    def new_settings_area(self, canvaswidth=300, linewidth=1):
            """
            creates a new backplate-canvas used as a settings area for smaller settings widgets
            it may be convenient to use linewidth to give it a nice looking frame
            :param canvaswidth: int
            :param linewidth: int
            :return: QtWidgets.QLabel
            """
            if 'blackgrays' not in dir(self):
                self.blackgrays = []

            black = t.pos(new=self, width=canvaswidth)
            t.style(black, background='gray', color='black')
            black.setFrameShape(QtWidgets.QFrame.Box)
            black.setLineWidth(linewidth)
            black.widgets = []

            self.blackgrays.append(black)
            return black

    def giveback_specific_widgetclass_or_default(self, dictionary, checkable=False, LCD=False, lineedit=False):
        if 'widget' not in dictionary:
            if checkable:
                return CheckableWidget # returns default
            elif LCD:
                return CountLabel
            elif lineedit:
                return FolderSettingsWidget
        else:
            return dictionary['widget'] # returns specific

    def get_add_from_toolsheight(self, linewidth):
        if linewidth - 1 < 2:
            inside_margin = 2
        else:
            inside_margin = linewidth - 1

        return inside_margin - 1

    def place_out_widgets_inside_settings_area(self, settingscanvas, label, previous_labels, toolsheight=30):
        linewidth = settingscanvas.lineWidth()
        margin = self.get_add_from_toolsheight(linewidth)

        if not previous_labels: # meaning we are first here to set the position
            t.pos(self, width=settingscanvas, height=toolsheight + margin * 2 + linewidth * 2)
            t.pos(label, inside=self, move=[margin + linewidth, margin + linewidth])
            t.pos(label, width=settingscanvas.width() - margin * 2 - linewidth * 2)
        else:
            t.pos(label, coat=previous_labels[-1], below=previous_labels[-1], y_margin=margin)

        t.pos(settingscanvas, height=label.geometry().bottom()+1, add=margin + linewidth)

        self.expand_me(settingscanvas) # todo not optimized to do this each time we call this fn

    def set_its_tooltip(self, label, dictionary):
        if 'tooltip' in dictionary:
            label.setToolTip(dictionary['tooltip'])

    def make_me_and_giveback_previous(self, settingscanvas, dictionary, headersdictionary, **kwargs):
        widget = self.giveback_specific_widgetclass_or_default(dictionary, **kwargs)
        previous = [x['label'] for x in headersdictionary if 'label' in x.keys()]
        label = widget(settingscanvas, main=self.main, **dictionary['kwargs'])
        self.set_its_tooltip(label, dictionary)
        return label, previous

    def delayed_init(self, dictionary, force=False):
        if 'post_init' in dictionary or force and 'label' in dictionary:
            dictionary['label'].post_init()

    def make_this_into_checkable_buttons(self, headersdictionary, toolsheight=30, canvaswidth=300, linewidth=1):
        """
        needs dict(text="HEADER TITLE", conf="widget_type") in order
        to do cheackable widget, the first will be positioned on top with toolsheight
        and uses settingscanvases width, the rest are following the first one
        :param headersdictionary:
        :param toolsheight: int (usually to give first widget a height, others follow)
        """
        settingscanvas = self.new_settings_area(canvaswidth, linewidth)

        for dictionary in headersdictionary:

            label, previous = self.make_me_and_giveback_previous(
                settingscanvas, dictionary, headersdictionary, checkable=True)

            self.place_out_widgets_inside_settings_area(settingscanvas, label,
                                                        toolsheight=toolsheight, previous_labels=previous)

            dictionary.update(dict(label=label, settingscanvas=settingscanvas))
            label.draw_checkable_widget(dictionary)  # todo not pretty some work was offloaded on child
            settingscanvas.widgets.append(dictionary)

            self.delayed_init(dictionary)

        return settingscanvas

    def make_this_into_LCDrow(self, headersdictionary, toolsheight=30, canvaswidth=300, linewidth=1):
        """
        row with LCD widgets uses almost identical methods as fn:make_this_into_checkable_buttons
        differences are LCD=True and label.draw_lcd_widget
        """
        def unpack_keywords(dictionary):
            text = ' ' + dictionary['text']
            type = dictionary['kwargs']['type']

            if 'lcds_in_this_row' in dictionary:
                lcds_in_this_row = dictionary['lcds_in_this_row']
            else:
                lcds_in_this_row = 3

            if 'max_value' in dictionary:
                max_value = dictionary['max_value']
            else:
                max_value = int('9' * lcds_in_this_row)

            if 'min_value' in dictionary:
                min_value = dictionary['min_value']
            else:
                min_value = 0

            return text, type, lcds_in_this_row, max_value, min_value

        settingscanvas = self.new_settings_area(canvaswidth, linewidth)

        for dictionary in headersdictionary:
            text, type, lcds_in_this_row, max_value, min_value = unpack_keywords(dictionary)

            label, previous = self.make_me_and_giveback_previous(
                settingscanvas, dictionary, headersdictionary, LCD=True)

            self.place_out_widgets_inside_settings_area(settingscanvas, label,
                                                        toolsheight=toolsheight, previous_labels=previous)
            label.make_title_label(text=text)
            lcds = label.draw_lcd_widget(
                type=type, lcds_in_this_row=lcds_in_this_row, max_value=max_value, min_value=min_value)

            margin = self.get_add_from_toolsheight(linewidth)
            for i in lcds:
                t.pos(i, move=[-margin -linewidth,0])

            label.extend_title_to_reach_lcd() # keeps title and lcd's appart
            dictionary.update(dict(label=label, lcd=lcds[0]))
            settingscanvas.widgets.append(dictionary)
            self.delayed_init(dictionary)

        return settingscanvas

    def make_this_into_checkable_button_with_LCDrow(self, headersdictionary, toolsheight=30, canvaswidth=300):
        """
        this highjacks fn: make_this_into_LCDrow and then makes the clickable
        button upon that label and moves the title_label so they all fit nicley
        to separate button_type from LCD_type we add _lcd to LCD_type
        :return: settingscanvas made via fn:make_this_into_LCDrow
        """
        for dictionary in headersdictionary:
            dictionary['kwargs']['type'] += '_lcd' # adds _lcd to self.type

        settingscanvas = self.make_this_into_LCDrow(headersdictionary, toolsheight, canvaswidth)

        for dictionary in headersdictionary:
            # for excplicity reasons dictionary changes back to previous type
            dictionary['kwargs']['type'] = dictionary['kwargs']['type'][0:-len('_lcd')]

            label = dictionary['label']
            label.type = dictionary['kwargs']['type'] # changes "back" into correct type before init
            label.draw_checkable_widget(dictionary)
            dictionary['textlabel'].close() # figure its easier to kill extra label than rewrite the fn
            dictionary.pop('textlabel') # excplicitly removes the textlabel from dictionary, not needed
            label.extend_title_to_reach_lcd() # might not be nessesary, just in case it pops out somewhere
            t.pos(label.title_label, move=[label.height(),0])
            self.delayed_init(dictionary)

        return settingscanvas

    def make_this_into_folder_settings(self, headersdictionary, toolsheight=30, labelwidth=240, le_width=500, linewidth=1, extend_le_til=None):
        """
        this is esentially a fn:make_this_into_checkable_buttons but adds a lineedit and
        attaches is as label.lineedit and resizes the settingscanvas accordingly
        """
        settingscanvas = self.new_settings_area(labelwidth, linewidth)

        for dictionary in headersdictionary:

            label, previous = self.make_me_and_giveback_previous(
                settingscanvas, dictionary, headersdictionary, lineedit=True)

            self.place_out_widgets_inside_settings_area(settingscanvas, label,
                                                        toolsheight=toolsheight, previous_labels=previous)

            label.lineedit = QtWidgets.QLineEdit(settingscanvas)
            label.lineedit.show()

            margin = self.get_add_from_toolsheight(linewidth)

            if extend_le_til:
                t.pos(settingscanvas, width=extend_le_til)
                t.pos(label.lineedit, coat=label, after=label)
                t.pos(label.lineedit, left=label.lineedit, right=settingscanvas, x_margin=margin)
            else:
                t.pos(label.lineedit, coat=label, after=label, x_margin=margin, width=le_width)

            t.pos(settingscanvas, width=label.lineedit.geometry().right(), add=margin)
            t.pos(label.lineedit, width=label.lineedit.width() - margin - linewidth)

            dictionary.update(dict(label=label, le=label.lineedit))
            label.draw_checkable_widget(dictionary)  # todo not pretty some work was offloaded on child
            settingscanvas.widgets.append(dictionary)
            self.delayed_init(dictionary, force=True)

        return settingscanvas



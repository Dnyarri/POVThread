#!/usr/bin/env python3

"""
======================================
Adaptive color average image filtering
======================================

Averaging image colors in a pixel row until difference between averaged
and next pixel in a row reach threshold. Then repeat the same in column.
Thus filter changes smooth image areas to completely flat colored,
with detailed edges between them.

`Averager`_ was initially created as `POV-Ray Thread`_ auxiliary
but later on evolved from small accessory for testing filter module
to an interesting example of pure Python image filtering application.

Input: PNG, PPM, PGM, PBM.

Output: PNG, PPM, PGM.

----
Main site: `The Toad's Slimy Mudhole`_

.. _The Toad's Slimy Mudhole: https://dnyarri.github.io

`POV-Ray Thread`_ previews and description

.. _POV-Ray Thread: https://dnyarri.github.io/povthread.html

`Averager`_ previews and description

.. _Averager: https://dnyarri.github.io/povthread.html#averager

POV-Ray Thread Git repositories: main `@Github`_ and mirror `@Gitflic`_

.. _@Github: https://github.com/Dnyarri/POVThread

.. _@Gitflic: https://gitflic.ru/project/dnyarri/povthread

"""

# History:
# --------
# 0.10.14.0     Initial version of filter host template - 14 Oct 2024.
#               Using png in tempfile preview etc.
# 0.10.17.3     Linked standalone version.
# 1.14.1.1      Preview etc with builtin PyPNM. Image list moved to global
#               to reduce rereading.
# 1.16.4.24     PNG and PPM support, zoom in and out, numerous fixes.
# 1.16.9.14     Preview switch source/result added. Zoom on click now mimic
#               Photoshop Ctrl + Click and Alt + Click.
# 2.16.20.20    Changed GUI to menus.
# 3.20.8.8      Changed GUI to grid to fit all new features. More detailed image info;
#               image mode and edited/saved status displayed in window title
#               and task manager) a-la Photoshop.
# 1.23.1.1      Even more GUI improvements, including spinbox control with mousewheel.
# 3.24.14.14    Suitable filter execution time display added to info string.
#               Result may be copied to clipboard on info string Ctrl+Click.
# 3.26.8.8      Several bugs fixed, memory requirements reduced due to substantial
#               onSave() changes. New bugs are highly likely to arise,
#               yet not found yet.
# 3.26.20.8     Better Spinbox validation.
# 3.28.8.8      UI have the potential to become standard.
# 3.29.26.6     Introducing draggable canvas (somewhat jaggy).
# 3.31.31.3     Cleanup and beautification.
# 3.32.22.8     With more UI improvements "Averager" becomes a GUI standard ;-)
# 3.33.1.7      Further GUI code generalization; var docstrings added.
# 4.34.9.9      Changed GUI from single window to modular to improve screen usage.
# 4.34.14.4     Substantial internal changes in GUI code, including windows restructure.
# 4.34.17.21    Gradually moving common binding and properties to dictionaries.

__author__ = 'Ilya Razmanov'
__copyright__ = '(c) 2024-2026 Ilya Razmanov'
__credits__ = 'Ilya Razmanov'
__license__ = 'unlicense'
__version__ = '4.34.24.24'  # 'Averager' 24 Oct 2026, 'filter' v. 4
__maintainer__ = 'Ilya Razmanov'
__email__ = 'ilyarazmanov@gmail.com'
__status__ = 'Production'

from copy import deepcopy
from pathlib import Path
from random import randbytes  # Used for random icon only
from time import ctime, time
from tkinter import BooleanVar, Button, Canvas, Checkbutton, Frame, IntVar, Label, LabelFrame, Menu, Menubutton, PhotoImage, Spinbox, TclError, Tk, Toplevel
from tkinter.filedialog import askopenfilename, asksaveasfilename
from tkinter.messagebox import showinfo  # Used for "Image Info" and "Help"

from filter import filter
from pypng import list2png, png2list
from pypnm import list2bin, list2pnm, pnm2list

""" ╔══════════════════════════════════╗
    ║ GUI events and functions thereof ║
    ╚══════════════════════════════════╝ """


def DisMiss(event=None) -> None:
    """Kill dialog and continue."""

    sortir.destroy()


def ShowMenu(event) -> None:
    """Pop menu up (or sort of drop it down)."""

    menu_file.post(event.x_root, event.y_root)


def ShowInfo(event=None) -> None:
    """Show image information."""

    file_size = Path(sourcefilename).stat().st_size
    file_size_str = f'{file_size / 1048576:.2f} Mb' if (file_size > 1048576) else f'{file_size / 1024:.2f} Kb' if (file_size > 1024) else f'{file_size} bytes'
    showinfo(
        title='Image information',
        message=f'File properties:\nLocation: {sourcefilename}\nSize: {file_size_str}\nLast modified: {ctime(Path(sourcefilename).stat().st_mtime)}',
        detail=f'Image properties, as represented internally:\nStatus: {is_filtered=}, {is_saved=}\nWidth: {X} px\nHeight: {Y} px\nChannels: {Z} channel{"s" if Z > 1 else ""}\nColor depth: {maxcolors + 1} gradations/channel',
    )


def ShowHelp(event=None) -> None:
    """Show some help info."""

    showinfo(
        title=f'{product_name} quick help',
        message=f'{product_name} {__version__} is a program averaging image pixels in a row until threshold of maximal difference between source and average hit, then repeating the same in a column.\nMain GUI functions are listed below:',
        detail=f'{help_str}\nInfo bar:\n Ctrl+Click copies last operation timing to clipboard;\n Alt+Click starts/stops continuous copying for every operation.\n\nRunning under Python  {VER}, free threading is {NOGIL}, PyPNM {__version__} {SUBVERSION}',
    )


def UINormal() -> None:
    """Normal UI state, buttons enabled."""

    for widget in frame_top.winfo_children():
        if widget.winfo_class() in ('Label', 'Button', 'Spinbox', 'Checkbutton'):
            widget['state'] = 'normal'
    info_string.config(text=info_normal['txt'], foreground=info_normal['fg'], background=info_normal['bg'])
    if Z in (1, 3):
        check_keep_alpha['state'] = 'disabled'
    whoever['cursor'] = sortir['cursor'] = zanyato['cursor'] = ''
    zanyato['state'] = 'normal'
    sortir.update()


def UIBusy() -> None:
    """Busy UI state, buttons disabled."""

    for widget in frame_top.winfo_children():
        if widget.winfo_class() in ('Label', 'Button', 'Spinbox', 'Checkbutton'):
            widget['state'] = 'disabled'
    info_string.config(text=f'BUSY {operation.upper()}', foreground=info_busy['fg'], background=info_busy['bg'])
    try:  # trying to be cross-platform, based on ``Python312\tcl\tk8.6\ttk\cursors.tcl``
        whoever['cursor'] = sortir['cursor'] = zanyato['cursor'] = 'wait'
    except TclError:
        whoever['cursor'] = sortir['cursor'] = zanyato['cursor'] = 'watch'
    zanyato['state'] = 'disabled'
    sortir.update()


def UIFit() -> None:
    """Readopting ``sortir.minsize`` to fit the screen."""

    sortir.update()
    fit_width, fit_height = (
        min(sortir.winfo_reqwidth(), 9 * sortir.winfo_screenwidth() // 10),
        min(sortir.winfo_reqheight(), 9 * sortir.winfo_screenheight() // 10),
    )
    sortir.minsize(fit_width, fit_height)


def canvasCoord(event):
    """Marking ``canvas`` click pont for further dragging."""

    canvas.scan_mark(event.x, event.y)


def canvasDrag(event):
    """Dragging ``canvas`` Canvas."""

    canvas.scan_dragto(
        event.x,
        event.y,
        gain=1,
    )
    canvas['cursor'] = 'fleur'


def ShowPreview(preview_choice: PhotoImage, caption: str) -> None:
    """Show ``preview_choice`` PhotoImage, trying to fit ``canvas`` to screen."""

    global preview

    # ↓ Copying parameter to global, required for Tkinter.
    preview = preview_choice
    # ↑ BTW `preview is preview_choice` returns `True`
    frame_preview.config(text=f'Filter {caption.lower()}')
    if zoom_factor > 0:
        preview = preview.zoom(zoom_factor + 1)
        label_zoom['text'] = f'{caption} {zoom_factor + 1}:1'
    elif zoom_factor < 0:
        preview = preview.subsample(1 - zoom_factor)
        label_zoom['text'] = f'{caption} 1:{1 - zoom_factor}'
    else:
        label_zoom['text'] = f'{caption} 1:1'

    # ↓ Sizes of preview to fit the screen
    zanyato.config(
        image=preview,
        relief='flat',  # Other reliefs seem to interfere with image
    )
    preview_width, preview_height = (
        min(preview.width(), 9 * sortir.winfo_screenwidth() // 10),
        min(preview.height(), (9 * sortir.winfo_screenheight() // 10) - frame_zoom.winfo_reqheight() - 20),
    )
    canvas.config(
        width=preview_width,
        height=preview_height,  # Note that 'scrollregion' may be bigger than canvas!
        scrollregion=(0, 0, preview.width(), preview.height()),
        cursor='arrow',
    )
    canvas.itemconfig(  # configuring 'zanyato' size in a normal way doesn't work on canvas
        zanyato_,
        width=preview.width(),
        height=preview.height(),
    )


def SwitchView(event=None) -> None:
    """Switch preview between ``preview_src`` and ``preview_filtered``."""

    global view_src

    view_src = not view_src
    if view_src or is_saved:
        ShowPreview(preview_src, 'Source')
    else:
        ShowPreview(preview_filtered, 'Result')


def GetSource(event=None) -> None:
    """Open source image and redefine other controls state."""

    global zoom_factor, view_src, is_filtered, is_saved, info_normal, color_mode_str, operation, timing
    global preview, preview_src, preview_filtered  # preview and copies of preview
    global sourcefilename, X, Y, Z, maxcolors, source_image, info  # everything about source
    global result_image  # deep copy of source_image to avoid cumulative filtering

    operation = 'Opening'

    # ↓ Intercept TclError caused by "" input before .get() cause it.
    try:
        _ = ini_threshold_x.get()
        ini_threshold_x.set(int(_))  # removes "-0", "00" etc.
    except TclError:
        ini_threshold_x.set(0)
    try:
        _ = ini_threshold_y.get()
        ini_threshold_y.set(int(_))
    except TclError:
        ini_threshold_y.set(0)

    # ↓ Temporary saving info in case of "Open.." cancel
    old_sourcefilename = sourcefilename
    # ↓ Opening "Open.." dialog
    sourcefilename = askopenfilename(
        title='Open image file',
        filetypes=[
            ('Supported formats', '.png .ppm .pgm .pbm .pnm'),
            ('Portable network graphics', '.png'),
            ('Portable any map', '.ppm .pgm .pbm .pnm'),
        ],
    )
    if sourcefilename == '':
        sourcefilename = old_sourcefilename
        return

    # ↓ Next must be set AFTER "sourcefilename", in case of "Open.." cancel
    zoom_factor = 0
    view_src = is_saved = True
    is_filtered = False

    UIBusy()
    start = time()
    if Path(sourcefilename).suffix.lower() == '.png':
        # ↓ Reading PNG image as list. Unpredictably, tuplevel='image' makes filter faster.
        X, Y, Z, maxcolors, source_image, info = png2list(sourcefilename, tuplevel='image')

    elif Path(sourcefilename).suffix.lower() in ('.ppm', '.pgm', '.pbm', '.pnm'):
        # ↓ Reading PNM image as list. Unpredictably, tuplevel='image' makes filter faster.
        X, Y, Z, maxcolors, source_image = pnm2list(sourcefilename, tuplevel='image')
        # ↓ Creating dummy info required to correctly Save As PNG later.
        #   Fixing color mode, the rest is fixed with pnglpng v. 25.01.07.
        info = {'bitdepth': 16} if maxcolors > 255 else {'bitdepth': 8}

    else:
        raise ValueError('Extension not recognized')
    timing = time() - start
    if logging:
        whoever.clipboard_append(f'{operation} {timing}\n')

    # ↓ Creating deep copy of source 3D list
    #   to avoid accumulating repetitive filtering.
    result_image = deepcopy(source_image)

    """ ┌───────────────┐
        │ Viewing image │
        └───────────────┘ """
    # ↓ Converting list to bytes of PNM-like structure "preview_data" in memory
    operation = 'Preview'
    start = time()
    preview_data = list2bin(result_image, maxcolors, show_chessboard=True)
    timing = time() - start
    if logging:
        whoever.clipboard_append(f'{operation} {timing}\n')
    # ↓ Now generating preview from "preview_data" bytes using Tkinter
    preview = PhotoImage(data=preview_data)

    # ↓ Creating copy of source preview for further
    #   fast switch between source and result.
    preview_src = preview_filtered = preview

    # ↓ Calculate zoom factor for "Zoom to fit".
    if preview.width() > sortir.winfo_screenwidth() or (128 + preview.height()) > sortir.winfo_screenheight():
        zoom_factor = max(-max(preview.width() // sortir.winfo_screenwidth(), (128 + preview.height() + frame_zoom.winfo_reqheight()) // sortir.winfo_screenheight()), minizoom)

    # ↓ Finally the show part
    ShowPreview(preview, 'Source')

    # ↓ Binding preview click and mouse drag
    for happens, function in bind.items():
        zanyato.bind(happens, function)
    # ↓ Binding global
    sortir.bind_all('<Return>', RunFilter)
    sortir.bind_all('<MouseWheel>', zoomWheel)  # Wheel scroll
    sortir.bind_all('<Control-i>', ShowInfo)
    menu_file.entryconfig('Image Info...', state='normal')
    # ↓ Enabling 'Save as...'
    menu_file.entryconfig('Save as...', state='normal')
    sortir.bind_all('<Control-Shift-S>', SaveAs)
    # ↓ Enabling zoom buttons
    butt_plus.config(state='normal', cursor='hand2')
    butt_minus.config(state='normal', cursor='hand2')
    # ↓ Adding filename, mode and status to window title a-la Photoshop
    if Z == 1:
        color_mode_str = f' (L:{"8" if maxcolors < 256 else "16"})'
    elif Z == 2:
        color_mode_str = f' (LA:{"8" if maxcolors < 256 else "16"})'
    elif Z == 3:
        color_mode_str = f' (RGB:{"8" if maxcolors < 256 else "16"})'
    elif Z == 4:
        color_mode_str = f' (RGBA:{"8" if maxcolors < 256 else "16"})'
    else:
        color_mode_str = ''  # Just in case
    sortir.title(f'{Path(sourcefilename).name}{color_mode_str}{"*" if is_filtered else ""} | VidWindow')
    info_normal = {'txt': f'{Path(sourcefilename).name}{"*" if is_filtered else ""} X={X} Y={Y} Z={Z} maxcolors={maxcolors}', 'fg': 'grey', 'bg': 'grey90'}
    # ↓ "Filter" mouseover
    butt_filter.bind('<Enter>', lambda event=None: butt_filter.config(foreground=butt['activeforeground'], background=butt['activebackground']))
    butt_filter.bind('<Leave>', lambda event=None: butt_filter.config(foreground=butt['foreground'], background=butt['background']))
    # ↓ Checkbox mouseovers
    if Z in (1, 3):
        check_keep_alpha.unbind('<Enter>')
        check_keep_alpha.unbind('<Leave>')
        ini_keep_alpha.set(False)
    else:
        check_keep_alpha.bind('<Enter>', lambda event=None: check_keep_alpha.config(foreground=butt['activeforeground'], background=butt['activebackground']))
        check_keep_alpha.bind('<Leave>', lambda event=None: check_keep_alpha.config(foreground=butt['foreground'], background=butt['background']))
    check_wraparound.bind('<Enter>', lambda event=None: check_wraparound.config(foreground=butt['activeforeground'], background=butt['activebackground']))
    check_wraparound.bind('<Leave>', lambda event=None: check_wraparound.config(foreground=butt['foreground'], background=butt['background']))
    # ↓ Spinbox mouseovers
    spin_x.bind('<Enter>', lambda event=None: spin_x.config(foreground=butt['activeforeground'], background=butt['activebackground']))
    spin_x.bind('<Leave>', lambda event=None: spin_x.config(foreground=butt['foreground'], background='white'))
    spin_y.bind('<Enter>', lambda event=None: spin_y.config(foreground=butt['activeforeground'], background=butt['activebackground']))
    spin_y.bind('<Leave>', lambda event=None: spin_y.config(foreground=butt['foreground'], background='white'))
    # ↓ Spinbox mouse input
    spin_x.unbind('<MouseWheel>')
    spin_x.bind('<MouseWheel>', incWheel)
    spin_y.unbind('<MouseWheel>')
    spin_y.bind('<MouseWheel>', incWheel)
    UINormal()
    UIFit()
    sortir.geometry(f'{sortir.winfo_reqwidth()}x{sortir.winfo_reqheight()}')
    whoever.geometry(f'{whoever.winfo_reqwidth()}x{whoever.winfo_reqheight()}')  # width may change!
    zanyato.focus_set()


def RunFilter(event=None) -> None:
    """Filter image, then preview result."""

    global view_src, is_filtered, is_saved, info_normal, operation, timing, preview_filtered, result_image

    # ↓ Intercept TclError caused by "" input before .get() cause it.
    try:
        _ = ini_threshold_x.get()
        ini_threshold_x.set(int(_))  # removes "-0", "00" etc.
    except TclError:
        ini_threshold_x.set(0)
    try:
        _ = ini_threshold_y.get()
        ini_threshold_y.set(int(_))
    except TclError:
        ini_threshold_y.set(0)

    operation = 'Filtering'

    # ↓ Now .get() filtering parameters
    threshold_x = maxcolors * ini_threshold_x.get() // 255  # Rescaling for 16-bit
    threshold_y = maxcolors * ini_threshold_y.get() // 255
    wraparound = ini_wraparound.get()
    keep_alpha = ini_keep_alpha.get()

    UIBusy()

    """ ┌─────────────────┐
        │ Filtering image │
        └─────────────────┘ """
    start = time()
    result_image = filter(source_image, threshold_x, threshold_y, wraparound, keep_alpha)
    timing = time() - start
    if logging:
        whoever.clipboard_append(f'{operation} {timing}\n')

    # ↓ Preview
    operation = 'Preview'
    start = time()
    preview_data = list2bin(result_image, maxcolors, show_chessboard=True)
    timing = time() - start
    if logging:
        whoever.clipboard_append(f'{operation} {timing}\n')
    preview_filtered = PhotoImage(data=preview_data)

    # ↓ Flagging as filtered, not saved
    is_filtered = True
    is_saved = view_src = False

    ShowPreview(preview_filtered, 'Result')

    # ↓ Enabling save
    menu_file.entryconfig('Save', state='normal')
    # ↓ Binding global
    sortir.bind_all('<Control-s>', Save)
    # ↓ Binding switch on preview click
    zanyato.bind('<Button-1>', SwitchView)
    zanyato.bind('<ButtonRelease-1>', SwitchView)
    zanyato.bind('<space>', SwitchView)
    # ↓ Adding filename, mode and status to window title a-la Photoshop
    sortir.title(f'{Path(sourcefilename).name}{color_mode_str}{"*" if is_filtered else ""} | VidWindow')
    info_normal = {'txt': f'{Path(sourcefilename).name}{"*" if is_filtered else ""} X={X} Y={Y} Z={Z} maxcolors={maxcolors}', 'fg': 'grey', 'bg': 'grey90'}
    UINormal()
    whoever.geometry(f'{whoever.winfo_reqwidth()}x{whoever.winfo_reqheight()}')
    zanyato.focus_set()  # moving focus to preview


def zoomIn(event=None) -> None:
    """Zoom preview in."""

    global zoom_factor

    zoom_factor = min(zoom_factor + 1, maxizoom)

    if view_src:
        ShowPreview(preview_src, 'Source')
    else:
        ShowPreview(preview_filtered, 'Result')

    # ↓ Reenabling +/- buttons
    butt_minus.config(state='normal', cursor='hand2')
    if zoom_factor == maxizoom:
        butt_plus.config(state='disabled', cursor='arrow')
    else:
        butt_plus.config(state='normal', cursor='hand2')
    UIFit()


def zoomOut(event=None) -> None:
    """Zoom preview out."""

    global zoom_factor

    zoom_factor = max(zoom_factor - 1, minizoom)

    if view_src:
        ShowPreview(preview_src, 'Source')
    else:
        ShowPreview(preview_filtered, 'Result')

    # ↓ Reenabling +/- buttons
    butt_plus.config(state='normal', cursor='hand2')
    if zoom_factor == minizoom:
        butt_minus.config(state='disabled', cursor='arrow')
    else:
        butt_minus.config(state='normal', cursor='hand2')
    UIFit()
    # ↓ Reducing 'VidWindow' size when zooming out
    sortir.geometry(f'{sortir.winfo_reqwidth()}x{sortir.winfo_reqheight()}')


def zoomOne(event=None) -> None:
    """Zoom 1:1."""

    global zoom_factor

    zoom_factor = 0

    if view_src:
        ShowPreview(preview_src, 'Source')
    else:
        ShowPreview(preview_filtered, 'Result')

    # ↓ Reenabling +/- buttons
    butt_plus.config(state='normal', cursor='hand2')
    butt_minus.config(state='normal', cursor='hand2')
    UIFit()
    # ↓ Reducing 'VidWindow' size in case when zoom 1:1 is zooming out
    sortir.geometry(f'{sortir.winfo_reqwidth()}x{sortir.winfo_reqheight()}')


def zoomWheel(event) -> None:
    """``zoomIn`` or ``zoomOut`` by mouse wheel."""

    if event.widget not in transparent_controls:
        if event.delta < 0:
            zoomOut()
        if event.delta > 0:
            zoomIn()


def onSave() -> None:
    """Reassign images and other objects from new to old upon saving."""

    global preview_src, info_normal, sourcefilename, source_image

    # ↓ Saved file becomes new source file
    sourcefilename = resultfilename
    source_image = result_image
    preview_src = preview_filtered

    # ↓ Disabling save
    menu_file.entryconfig('Save', state='disabled')
    sortir.unbind_all('<Control-s>')
    # ↓ Binding switch on preview click
    zanyato.unbind('<Button-1>')  # left click
    zanyato.unbind('<space>')
    # ↓ Preview source
    ShowPreview(preview_src, 'Source')
    # ↓ Adding filename, mode and status to window title a-la Photoshop
    sortir.title(f'{Path(sourcefilename).name}{color_mode_str}{"*" if is_filtered else ""} | VidWindow')
    info_normal = {'txt': f'{Path(sourcefilename).name}{"*" if is_filtered else ""} X={X} Y={Y} Z={Z} maxcolors={maxcolors}', 'fg': 'grey', 'bg': 'grey90'}
    UINormal()


def Save(event=None) -> None:
    """Once pressed on ``Save``."""

    global is_filtered, is_saved, operation, timing, resultfilename

    operation = 'Saving'

    if is_saved:  # block repetitive saving
        return
    if not is_filtered:  # block useless source resaving
        return
    resultfilename = sourcefilename
    UIBusy()
    start = time()
    # ↓ Save format choice
    if Path(resultfilename).suffix.lower() == '.png':
        info['compression'] = 9  # Explicitly setting compression
        list2png(resultfilename, result_image, info)  # Writing file
    elif Path(resultfilename).suffix.lower() in ('.ppm', '.pgm', '.pnm'):
        list2pnm(resultfilename, result_image, maxcolors)  # Writing file
    timing = time() - start
    if logging:
        whoever.clipboard_append(f'{operation} {timing}\n')

    # ↓ Flagging image as saved, not filtered
    is_saved = True  # to block future repetitive saving
    is_filtered = False
    # ↓ Saved file becomes new source file
    onSave()
    UINormal()


def SaveAs(event=None) -> None:
    """Once pressed on ``Save as...``"""

    global is_saved, is_filtered, operation, timing, resultfilename

    operation = 'Saving'

    # ↓ Adjusting "Save as..." formats to be displayed
    #   according to number of channels and source extension
    src_extension = Path(sourcefilename).suffix.lower()
    if Z == 1:
        if src_extension in ('.pgm', '.pnm'):
            format_list = [
                ('Portable grey map', '.pgm'),
                ('Portable network graphics', '.png'),
            ]
            proposed_name = Path(sourcefilename).stem + '.pgm'
        else:
            format_list = [
                ('Portable network graphics', '.png'),
                ('Portable grey map', '.pgm'),
            ]
            proposed_name = Path(sourcefilename).stem + '.png'
    elif Z == 2:
        format_list = [('Portable network graphics', '.png')]
        proposed_name = Path(sourcefilename).stem + '.png'
    elif Z == 3:
        if src_extension in ('.ppm', '.pnm'):
            format_list = [
                ('Portable pixel map', '.ppm'),
                ('Portable network graphics', '.png'),
            ]
            proposed_name = Path(sourcefilename).stem + '.ppm'
        else:
            format_list = [
                ('Portable network graphics', '.png'),
                ('Portable pixel map', '.ppm'),
            ]
            proposed_name = Path(sourcefilename).stem + '.png'
    else:
        format_list = [('Portable network graphics', '.png')]
        proposed_name = Path(sourcefilename).stem + '.png'

    # ↓ Open export file
    resultfilename = asksaveasfilename(
        title='Save image file',
        filetypes=format_list,
        defaultextension='.png',  # No extension should never happen but just in case
        initialdir=Path(sourcefilename).parent,
        initialfile=proposed_name,
    )
    if resultfilename == '':
        return
    UIBusy()
    start = time()
    # ↓ Save format choice
    if Path(resultfilename).suffix.lower() == '.png':
        info['compression'] = 9  # Explicitly setting compression
        list2png(resultfilename, result_image, info)  # Writing file
    elif Path(resultfilename).suffix.lower() in ('.ppm', '.pgm'):
        list2pnm(resultfilename, result_image, maxcolors)  # Writing file
    else:
        raise ValueError('Extension not recognized')
    timing = time() - start
    if logging:
        whoever.clipboard_append(f'{operation} {timing}\n')
    # ↓ Flagging image as saved, not filtered, and disabling "Save"
    is_saved = True  # to block future repetitive saving
    is_filtered = False
    # ↓ Saved file becomes new source file
    onSave()
    UINormal()


def valiDig(new_value):
    """Validate Spinbox input and reject non-integer."""

    if new_value == '':
        return True  # temporarily allow empty string, to be removed in RunFilter
    else:
        try:
            _ = int(new_value)
            return (-1 < _ < 256) or not (new_value.startswith('0') and int(new_value) != 0)
        except ValueError:
            return False


def incWheel(event) -> None:
    """Increment or decrement spinboxes by mouse wheel."""

    if event.widget == spin_x:
        if event.delta < 0:
            ini_threshold_x.set(min(255, max(0, ini_threshold_x.get() - threshold_increment)))
        if event.delta > 0:
            ini_threshold_x.set(min(255, max(0, ini_threshold_x.get() + threshold_increment)))
    if event.widget == spin_y:
        if event.delta < 0:
            ini_threshold_y.set(min(255, max(0, ini_threshold_y.get() - threshold_increment)))
        if event.delta > 0:
            ini_threshold_y.set(min(255, max(0, ini_threshold_y.get() + threshold_increment)))


def turnLogging(event=None):
    global logging
    logging = not logging
    whoever.clipboard_clear()
    whoever.focus_set()


""" ╒══════════════╕
    │ Initializing │
    ╰──────────────╯ """
product_name = 'Averager'
"""Program name."""

sourcefilename = ''
"""Name of file to be opened."""

zoom_factor = 0
"""Current zoom. Midpoint value 0 correspond to 1:1 zoom."""

view_src = True
"""Whether source image should be shown rather than the result."""

is_filtered = False
"""Whether image filtering was performed."""

is_saved = False
"""Whether image was saved after filtering was performed."""

timing = 0
"""Execution time for most recent operation."""

maxizoom = 4
"""Maximal zoom:1 for ZoomIn(). Mnemonic: "maxi" means "image look big"."""

minizoom = -4
"""Maximal 1:zoom for ZoomOut(). Mnemonic: "mini" means "image look small"."""

threshold_increment = 1
"""Threshold increment for incWheel() and spinboxes."""

color_mode_str = ' '
"""Image color mode info."""

# ↓ Info for debugging and help
try:
    from sys import _is_gil_enabled  # whether free threading EXIST in this Python version

    NOGIL = not _is_gil_enabled()  # whether free threading WORK in this Python build
except ImportError:  # old Python without free threading
    NOGIL = False

try:
    from platform import python_version

    VER = python_version()
except ImportError:
    VER = 'Unknown'

try:
    from pypnm import SUBVERSION
except ImportError:
    SUBVERSION = 'Unknown'

operation = f'Start Python {VER} {NOGIL=}'
"""Name of most recent operation timing was calculated for."""

logging = False
"""Whether to put log to clipboard."""

some_help = (
    'Preview area:',
    '  <Double click> to open image,',
    '  <Right click> or <Alt+F> for "File..." menu.',
    'With image opened:',
    '  <Ctrl+Click> to zoom in,',
    '  <Alt+Click> to zoom out,',
    '  <Ctrl+1> to zoom 1:1,',
    '  <Mouse wheel> to zoom in/out,',
    '  <Click+drag> to pan preview,',
    '  <Enter> to execute filter,',
    '  <Click> or <Space> to switch source/result view.',
)
"""Help ``tuple(str)`` to be used for both main window and F1."""

help_str = '\n'.join(some_help)
"""Help ``str`` to be used for both main window and F1."""

""" ╒═ Dictionaries ═════════════╕
    │ Bindings, properties, etc. │
    ╰────────────────────────────╯ """
# ↓ Most common bindings dictionaries
bind_all = {
    '<Button-3>': ShowMenu,
    '<Alt-f>': ShowMenu,
    '<Alt-F>': ShowMenu,
    '<F1>': ShowHelp,
    '<Control-o>': GetSource,
    '<Control-O>': GetSource,
    '<Control-q>': DisMiss,
    '<Control-Q>': DisMiss,
    '<Control-w>': DisMiss,
    '<Control-W>': DisMiss,
}
"""Main window bindings before image open, ``event: function`` pairs."""
bind = {
    '<Motion>': canvasCoord,
    '<B1-Motion>': canvasDrag,
    '<Control-Button-1>': zoomIn,
    '<Double-Control-Button-1>': zoomIn,
    '<Control-+>': zoomIn,
    '<Control-=>': zoomIn,
    '<Alt-Button-1>': zoomOut,
    '<Double-Alt-Button-1>': zoomOut,
    '<Control-minus>': zoomOut,
    '<Control-Key-1>': zoomOne,
    '<Control-Alt-Key-0>': zoomOne,
    '<ButtonRelease-1>': lambda event: canvas.config(cursor='arrow'),
}
"""Image Label bindings after image open, ``event: function`` pairs."""

# ↓ Buttons properties dictionary
butt = {
    'font': ('helvetica', 12),
    'cursor': 'hand2',
    'border': '2',
    'relief': 'groove',
    'overrelief': 'ridge',
    'foreground': 'SystemButtonText',
    'background': 'SystemButtonFace',
    'activeforeground': 'dark blue',
    'activebackground': '#E5F1FB',
}
"""Buttons properties dictionary, keys are ``font``, ``cursor``, ``border``,
    ``relief``, ``overrelief``, ``foreground``, ``background``,
    ``activeforeground``, ``activebackground``."""

# ↓ Info statuses dictionaries
info_normal = {
    'txt': f'Adaptive Average {__version__}',
    'fg': 'grey',
    'bg': 'grey90',
}
"""``info_string`` properties in normal state"""
info_busy = {
    'txt': 'BUSY, PLEASE WAIT',
    'fg': 'red',
    'bg': 'yellow',
}
"""``info_string`` properties in busy state"""

""" ╔═══════════╗
    ║ Main body ║
    ╚═══════════╝ """
sortir = Tk()
"""Main dialog window, containing ``frame_preview`` Frame."""
sortir.title(f'{product_name} | VidWindow')
sortir.iconphoto(True, PhotoImage(data=b''.join(('P6\n3 16\n255\n'.encode(encoding='ascii'), randbytes(3 * 16 * 3)))))

validate_entry = sortir.register(valiDig)
"""Name of ``validatecommand`` option for entries and spinboxes."""

whoever = Toplevel(sortir)
"""Whoever controls Dune."""
whoever.title(f'{product_name} {__version__} | Controls')
whoever.transient(sortir)  # make control panel always on top
whoever.protocol('WM_DELETE_WINDOW', lambda: None)  # block any attempt to close control panel
sortir.protocol('WM_DELETE_WINDOW', DisMiss)  # just to be temporarily explicit

# ↓ Info string
info_string = Label(
    whoever,
    text=info_normal['txt'],
    font=('helvetica', 8),
    foreground=info_normal['fg'],
    background=info_normal['bg'],
    relief='groove',
)
"""Info text label below main image, regularly updated."""
info_string.pack(side='bottom', padx=0, pady=(2, 0), fill='both')

""" ┌──────────────────────┐
    │ Top frame (controls) │
    └─────────────────────-┘ """
frame_top = Frame(whoever, borderwidth=2, relief='groove')
"""Frame containing controls."""
frame_top.pack(side='top', anchor='w', pady=(0, 2))

# ↓ File menu
butt_file = Menubutton(
    frame_top,
    text='File...',
    width=8,
    anchor='w',
    font=butt['font'],
    cursor=butt['cursor'],
    relief=butt['relief'],
    activeforeground=butt['activeforeground'],
    activebackground=butt['activebackground'],
    border=butt['border'],
    state='normal',
    indicatoron=False,
)
"""File menu button."""
butt_file.grid(row=0, column=0, rowspan=2, sticky='ns', padx=(0, 10), pady=0)

menu_file = Menu(butt_file, tearoff=False)
"""File menu."""
menu_file.add_command(label='Open...', state='normal', command=GetSource, accelerator='Ctrl+O')
menu_file.add_separator()
menu_file.add_command(label='Save', state='disabled', command=Save, accelerator='Ctrl+S')
menu_file.add_command(label='Save as...', state='disabled', command=SaveAs, accelerator='Ctrl+Shift+S')
menu_file.add_separator()
menu_file.add_command(label='Image Info...', accelerator='Ctrl+I', state='disabled', command=ShowInfo)
menu_file.add_separator()
menu_file.add_command(label='Help...', accelerator='F1', state='normal', command=ShowHelp)
menu_file.add_separator()
menu_file.add_command(label='Exit', state='normal', command=DisMiss, accelerator='Ctrl+Q')

butt_file['menu'] = menu_file  # Attach menu to menu button

butt_file.focus_set()  # Setting focus to "File..."

# ↓ Filter section begins
info_threshold = Label(frame_top, text='Filtering threshold:', font=('helvetica', 8, 'italic'), justify='right', foreground='brown', state='disabled')
info_threshold.grid(row=0, column=1)

# ↓ X-pass threshold control
info_threshold_x = Label(frame_top, text='X:', font=('helvetica', 11), state='disabled')
info_threshold_x.grid(row=0, column=2)

ini_threshold_x = IntVar(value=16)
"""Horizontal filtering threshold value."""
spin_x = Spinbox(
    frame_top,
    from_=0,
    to=255,
    increment=threshold_increment,
    textvariable=ini_threshold_x,
    state='disabled',
    width=3,
    font=('helvetica', 11),
    validate='key',
    validatecommand=(validate_entry, '%P'),
)
"""Horizontal filtering threshold control."""
spin_x.grid(row=0, column=3)

# ↓ Y-pass threshold control
info_threshold_y = Label(frame_top, text='Y:', font=('helvetica', 11), state='disabled')
info_threshold_y.grid(row=0, column=4)

ini_threshold_y = IntVar(value=8)
"""Vertical filtering threshold value."""
spin_y = Spinbox(
    frame_top,
    from_=0,
    to=255,
    increment=threshold_increment,
    textvariable=ini_threshold_y,
    state='disabled',
    width=3,
    font=('helvetica', 11),
    validate='key',
    validatecommand=(validate_entry, '%P'),
)
"""Vertical filtering threshold control."""
spin_y.grid(row=0, column=5)

# ↓ "Wrap around" control
ini_wraparound = BooleanVar(value=False)
"""Whether to process image wrap-around."""
check_wraparound = Checkbutton(
    frame_top,
    text='Wrap around',
    font=('helvetica', 9),
    variable=ini_wraparound,
    onvalue=True,
    offvalue=False,
    state='disabled',
    activeforeground=butt['activeforeground'],
    activebackground=butt['activebackground'],
)
"""Control whether to process image wrap-around."""
check_wraparound.grid(row=1, column=1, sticky='ws')

# ↓ "Keep alpha" control
ini_keep_alpha = BooleanVar(value=False)
"""Whether to copy source image alpha to result."""
check_keep_alpha = Checkbutton(
    frame_top,
    text='Keep alpha',
    font=('helvetica', 9),
    variable=ini_keep_alpha,
    onvalue=True,
    offvalue=False,
    state='disabled',
    activeforeground=butt['activeforeground'],
    activebackground=butt['activebackground'],
)
"""Control whether to copy source image alpha to result."""
check_keep_alpha.grid(row=1, column=3, columnspan=3, sticky='ws')

# ↓ Filter start
butt_filter = Button(
    frame_top,
    text='Filter',
    width=8,
    anchor='center',
    font=butt['font'],
    cursor='arrow',
    relief=butt['relief'],
    overrelief=butt['overrelief'],
    activeforeground=butt['activeforeground'],
    activebackground=butt['activebackground'],
    border=butt['border'],
    state='disabled',
    command=RunFilter,
)
"""Filter image button."""
butt_filter.grid(row=0, column=6, rowspan=2, sticky='nsew', padx=(10, 0), pady=0)

""" ┌──────────────────────────────┐
    │ Center frame (image preview) │
    └─────────────────────────────-┘ """
frame_preview = LabelFrame(
    sortir,
    text='Preview area',
    font=('helvetica', 8),
    relief='groove',
)
"""Frame containing main label (image preview) and zoom control subframe."""
frame_preview.pack(side='top', anchor='center', expand=True)

canvas = Canvas(
    frame_preview,
    borderwidth=1,
    highlightthickness=1,
    # background='red',  # forms internal border
    # highlightbackground='green',  # forms external border
    # highlightcolor='yellow',  # external border with opened image
)
"""Canvas containing preview."""
canvas.pack()

zanyato = Label(
    canvas,
    text=help_str.replace('<', '').replace('>', ''),
    font=('helvetica', 12),
    justify='left',
    padx=24,
    pady=24,
    borderwidth=2,
    background='grey90',
    relief='groove',
)
"""Main label containing canvas containing preview."""
zanyato.pack(side='top')

zanyato_ = canvas.create_window(
    0,
    0,
    window=zanyato,
    width=zanyato.winfo_reqwidth(),
    height=zanyato.winfo_reqheight(),
    anchor='nw',
)
"""Create/config canvas in main label."""

canvas.config(
    width=zanyato.winfo_reqwidth(),
    height=zanyato.winfo_reqheight(),
    scrollregion=(0, 0, zanyato.winfo_reqwidth(), zanyato.winfo_reqheight()),
)

frame_zoom = Frame(frame_preview, borderwidth=2, relief='groove')
"""Zoom control subframe."""
frame_zoom.pack(side='bottom')

butt_plus = Button(frame_zoom, text='+', font=('courier', 8), width=2, cursor='arrow', state='disabled', borderwidth=1, command=zoomIn)
butt_plus.pack(side='left', padx=0, pady=0, fill='both')

butt_minus = Button(frame_zoom, text='-', font=('courier', 8), width=2, cursor='arrow', state='disabled', borderwidth=1, command=zoomOut)
butt_minus.pack(side='right', padx=0, pady=0, fill='both')

label_zoom = Label(frame_zoom, text='Zoom 1:1', font=('courier', 8), state='disabled')
label_zoom.pack(side='left', anchor='n', padx=2, pady=0, fill='both')

# ↓ Spinboxes to be cut off global events and bound to spinbox events
transparent_controls = (spin_x, spin_y)
"""Controls to be uncontrolled by global events."""

""" ┌─────────────────────────────────────────────┐
    │ Binding everything that does not need image │
    └────────────────────────────────────────────-┘ """
# ↓ Info string binding for displaying filter execution time
info_string.bind('<Enter>', lambda event=None: info_string.config(text=f'{operation} time: {round(timing, 3)} sec (journal {"ON" if logging else "OFF"})'))
info_string.bind('<Leave>', lambda event=None: info_string.config(text=info_normal['txt']))
info_string.bind('<Control-Button-1>', lambda event=None: [whoever.clipboard_clear(), whoever.clipboard_append(f'{timing}\n')])
info_string.bind('<Alt-Button-1>', turnLogging)
# ↓ "File..." mouseover
butt_file.bind('<Enter>', lambda event=None: butt_file.config(relief=butt['overrelief']))
butt_file.bind('<Leave>', lambda event=None: butt_file.config(relief=butt['relief']))
# ↓ Double-click image area to "Open..."
zanyato.bind('<Double-Button-1>', GetSource)
frame_preview.bind('<Double-Button-1>', GetSource)
# ↓ Whole sortir binding menu, "Open..." and "Exit"
for happens, function in bind_all.items():
    sortir.bind_all(happens, function)

# ↓ Make Tkinter build GUI to make it calculate requested sizes.
sortir.update()
whoever.update()
whoever.resizable(False, False)

# ↓ Readopting minsize
UIFit()
whoever.minsize(whoever.winfo_reqwidth(), whoever.winfo_reqheight())
# ↓ Setting maxsize to fit 90% of screen
sortir.maxsize(9 * sortir.winfo_screenwidth() // 10, 9 * sortir.winfo_screenheight() // 10)
# ↓ Align windows and center window group horizontally, +64 vertically
sortir.geometry(f'+{(sortir.winfo_screenwidth() - sortir.winfo_width() - whoever.winfo_width() + 64) // 2}+64')
sortir.update()
whoever.geometry(f'+{sortir.winfo_rootx() + sortir.winfo_reqwidth() - 64}+{sortir.winfo_rooty() + 32}')

# ↓ Experimental alpha usage on focus. Looks good for useability but compatibility seems to suck.
"""whoever.bind('<Enter>', lambda event=None: whoever.attributes('-alpha', 0.9))
whoever.bind('<Leave>', lambda event=None: whoever.attributes('-alpha', 0.6))"""

sortir.mainloop()

#!/usr/bin/env python3

"""
==============
POV-Ray Thread
==============
------------------------------------------------------------------------
Converting image to canvas and cross stitch simulation in POV-Ray format
------------------------------------------------------------------------

Input: PNG, PPM, PGM.

Output: `POV-Ray <https://www.povray.org/>`_.

**POV-Ray Thread** provides converting images
and image-like nested lists to an assembly of 3D objects,
colored after source pixels, and forming a simulation of:

- plain weave textile (with "Linen" export);
- cross stitch (with "Stitch" export).

Objects may be displaced when rendering, based on POV-Ray internal
Perlin noise, simulating canvas deformation.

----
Main site: `The Toad's Slimy Mudhole`_

.. _The Toad's Slimy Mudhole: https://dnyarri.github.io

`POV-Ray Thread`_ previews and description

.. _POV-Ray Thread: https://dnyarri.github.io/povthread.html

POV-Ray Thread Git repositories: main `@Github`_ and mirror `@Gitflic`_

.. _@Github: https://github.com/Dnyarri/POVthread

.. _@Gitflic: https://gitflic.ru/project/dnyarri/povthread

"""

# History:
# --------
# 0.10.14.0     Initial version of filter host template - 14 Oct 2024. Using png in tempfile preview etc.
# 1.16.6.9      Public release of this GUI.
# 1.16.9.14     Preview switch source/result added. Zoom on click now mimic
#               Photoshop Ctrl + Click and Alt + Click.
# 1.16.20.20    Changed GUI to menus.
# 1.20.20.1     Numerous minor GUI improvements and code cleanup.
# 1.23.1.1      Even more numerous GUI improvements, including spinbox control with mousewheel.
# 1.26.8.8      Minimal debugging, some code restructure to simplify further editing.
# 1.26.20.8     Better Spinbox validation.
# 1.29.26.6     Introducing draggable canvas to keep UI in line with "Averager".
# 1.31.31.3     Cleanup and beautification.

__author__ = 'Ilya Razmanov'
__copyright__ = '(c) 2024-2026 Ilya Razmanov'
__credits__ = 'Ilya Razmanov'
__license__ = 'unlicense'
__version__ = '1.33.23.23'  # 'POV-Ray Thread' 23 Sep 2026, export modules v. 1
__maintainer__ = 'Ilya Razmanov'
__email__ = 'ilyarazmanov@gmail.com'
__status__ = 'Production'

from copy import deepcopy
from pathlib import Path
from random import randbytes
from time import ctime
from tkinter import Button, Canvas, Frame, IntVar, Label, Menu, Menubutton, PhotoImage, Spinbox, TclError, Tk
from tkinter.filedialog import askopenfilename, asksaveasfilename
from tkinter.messagebox import showinfo

from export import linen, stitch
from filter import filter
from pypng import png2list
from pypnm import list2bin, pnm2list

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
        detail=f'Image properties, as represented internally:\nWidth: {X} px\nHeight: {Y} px\nChannels: {Z} channel{"s" if Z > 1 else ""}\nColor depth: {maxcolors + 1} gradations/channel',
    )


def ShowHelp(event=None) -> None:
    """Show some help info."""

    showinfo(
        title=f'{product_name} quick help',
        message=f'{product_name} {__version__} is a program for converting 2D image into textile simulation, made of 3D objects.\nMain GUI functions are listed below:',
        detail=help_str,
    )


def UINormal() -> None:
    """Normal UI state, buttons enabled."""

    for widget in frame_top.winfo_children():
        if widget.winfo_class() in ('Label', 'Button', 'Spinbox'):
            widget['state'] = 'normal'
        if widget.winfo_class() == 'Button':
            widget['cursor'] = 'hand2'
        if widget.winfo_class() in ('Label',):
            widget['cursor'] = 'arrow'
    info_string.config(text=info_normal['txt'], foreground=info_normal['fg'], background=info_normal['bg'])
    sortir.update()


def UIBusy() -> None:
    """Busy UI state, buttons disabled."""

    for widget in frame_top.winfo_children():
        if widget.winfo_class() in ('Label', 'Button', 'Spinbox'):
            widget['state'] = 'disabled'
        if widget.winfo_class() == 'Button':
            widget['cursor'] = 'arrow'
    info_string.config(text=info_busy['txt'], foreground=info_busy['fg'], background=info_busy['bg'])
    sortir.update()


def UIFit() -> None:
    """Readopting 'sortir.minsize' to fit the screen."""

    sortir.update()
    fit_width, fit_height = (
        min(sortir.winfo_reqwidth(), 9 * sortir.winfo_screenwidth() // 10),
        min(sortir.winfo_reqheight(), 9 * sortir.winfo_screenheight() // 10),
    )
    sortir.minsize(fit_width, fit_height)


def canvasCoord(event):
    """Marking 'canvas' click pont for further dragging."""

    canvas.scan_mark(event.x, event.y)


def canvasDrag(event):
    """Dragging 'canvas' Canvas."""

    canvas.scan_dragto(
        event.x,
        event.y,
        gain=1,
    )
    canvas['cursor'] = 'fleur'


def ShowPreview(preview_choice: PhotoImage, caption: str) -> None:
    """Show 'preview_choice' PhotoImage, trying to fit 'canvas' to screen."""

    global preview

    preview = preview_choice

    if zoom_factor > 0:
        preview = preview.zoom(zoom_factor + 1)
        label_zoom['text'] = f'{caption} {zoom_factor + 1}:1'
    elif zoom_factor < 0:
        preview = preview.subsample(1 - zoom_factor)
        label_zoom['text'] = f'{caption} 1:{1 - zoom_factor}'
    else:
        label_zoom['text'] = f'{caption} 1:1'

    # ↓ Sizes of preview to fit the screen
    zanyato.config(image=preview, relief='flat')
    preview_width, preview_height = (
        min(preview.width(), 8 * sortir.winfo_screenwidth() // 10),
        min(preview.height(), (8 * sortir.winfo_screenheight() // 10) - frame_top.winfo_height() - info_string.winfo_height() - frame_zoom.winfo_height()),
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
    """Switch preview between preview_src and preview_filtered."""

    global view_src

    view_src = not view_src
    if view_src:
        ShowPreview(preview_src, 'Source')
    else:
        ShowPreview(preview_filtered, 'Result')


def GetSource(event=None) -> None:
    """Open source image and redefine other controls state."""

    global zoom_factor, view_src, info_normal
    global preview, preview_src, preview_filtered  # preview and copies of preview
    global sourcefilename, X, Y, Z, maxcolors, source_image, info
    global result_image  # deep copy of source_image to avoid cumulative filtering

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

    old_sourcefilename = sourcefilename  # Temporary saving info in case of "Open.." cancel
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
    view_src = True

    UIBusy()

    if Path(sourcefilename).suffix.lower() == '.png':
        # ↓ Reading PNG image as list
        X, Y, Z, maxcolors, source_image, info = png2list(sourcefilename)

    elif Path(sourcefilename).suffix.lower() in ('.ppm', '.pgm', '.pbm', '.pnm'):
        # ↓ Reading PNM image as list
        X, Y, Z, maxcolors, source_image = pnm2list(sourcefilename)

    else:
        raise ValueError('Extension not recognized')

    # ↓ Creating deep copy of source 3D list
    #   to avoid accumulating repetitive filtering.
    result_image = deepcopy(source_image)

    """ ┌───────────────┐
        │ Viewing image │
        └───────────────┘ """
    # ↓ Converting list to bytes of PPM-like structure "preview_data" in memory
    preview_data = list2bin(result_image, maxcolors, show_chessboard=True)
    # ↓ Now generating preview from "preview_data" bytes using Tkinter
    preview = PhotoImage(data=preview_data)

    # ↓ Creating copy of source preview for further
    #   fast switch between source and result.
    preview_src = preview_filtered = preview

    # ↓ Calculate zoom factor for "Zoom to fit".
    if preview.width() > sortir.winfo_screenwidth() or (128 + preview.height() + frame_top.winfo_reqheight()) > sortir.winfo_screenheight():
        zoom_factor = max(-max(preview.width() // sortir.winfo_screenwidth(), (128 + preview.height() + frame_top.winfo_reqheight() + frame_zoom.winfo_reqheight() + info_string.winfo_reqheight()) // sortir.winfo_screenheight()), minizoom)

    # ↓ Finally the show part
    ShowPreview(preview, 'Source')

    # ↓ Binding preview mouse drag
    zanyato.bind('<Motion>', canvasCoord)
    zanyato.bind('<B1-Motion>', canvasDrag)
    zanyato.bind('<ButtonRelease-1>', lambda event: canvas.config(cursor='arrow'))  # cursor back after drag
    # ↓ Binding preview click
    zanyato.bind('<Control-Button-1>', zoomIn)  # Ctrl + left click
    zanyato.bind('<Double-Control-Button-1>', zoomIn)  # Ctrl + left click too fast
    zanyato.bind('<Control-+>', zoomIn)
    zanyato.bind('<Control-=>', zoomIn)
    zanyato.bind('<Alt-Button-1>', zoomOut)  # Alt + left click
    zanyato.bind('<Double-Alt-Button-1>', zoomOut)  # Alt + left click too fast
    zanyato.bind('<Control-minus>', zoomOut)
    zanyato.bind('<Control-Key-1>', zoomOne)
    zanyato.bind('<Control-Alt-Key-0>', zoomOne)
    # ↓ Binding global
    sortir.bind_all('<Return>', RunFilter)
    sortir.bind_all('<MouseWheel>', zoomWheel)  # Wheel scroll
    sortir.bind_all('<Control-i>', ShowInfo)
    menu_file.entryconfig('Image Info...', state='normal')
    # ↓ Enabling 'Export...'
    menu_file.entryconfig('Export Linen...', state='normal')
    menu_file.entryconfig('Export Stitch...', state='normal')

    # ↓ Enabling zoom buttons
    butt_plus.config(state='normal', cursor='hand2')
    butt_minus.config(state='normal', cursor='hand2')
    # ↓ Adding filename to window title a-la Photoshop
    sortir.title(f'{product_name}: {Path(sourcefilename).name}')
    info_normal = {'txt': f'{Path(sourcefilename).name} X={X} Y={Y} Z={Z} maxcolors={maxcolors}', 'fg': 'grey', 'bg': 'grey90'}
    # ↓ "Filter" mouseover
    butt_filter.bind('<Enter>', lambda event=None: butt_filter.config(foreground=butt['activeforeground'], background=butt['activebackground']))
    butt_filter.bind('<Leave>', lambda event=None: butt_filter.config(foreground=butt['foreground'], background=butt['background']))
    # ↓ Spinbox mouseovers
    spin_x.bind('<Enter>', lambda event=None: spin_x.config(foreground=butt['activeforeground'], background=butt['activebackground']))
    spin_x.bind('<Leave>', lambda event=None: spin_x.config(foreground=butt['foreground'], background='white'))
    spin_y.bind('<Enter>', lambda event=None: spin_y.config(foreground=butt['activeforeground'], background=butt['activebackground']))
    spin_y.bind('<Leave>', lambda event=None: spin_y.config(foreground=butt['foreground'], background='white'))
    # ↓ Spinbox scroll
    spin_x.unbind('<MouseWheel>')
    spin_x.bind('<MouseWheel>', incWheel)
    spin_y.unbind('<MouseWheel>')
    spin_y.bind('<MouseWheel>', incWheel)
    UINormal()
    UIFit()
    sortir.geometry(f'+{(sortir.winfo_screenwidth() - sortir.winfo_width()) // 2}+64')
    zanyato.focus_set()


def RunFilter(event=None) -> None:
    """Filter image, then preview result."""

    global view_src
    global preview_filtered
    global result_image

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

    # ↓ Now .get() filtering parameters
    threshold_x = maxcolors * ini_threshold_x.get() // 255  # Rescaling for 16-bit
    threshold_y = maxcolors * ini_threshold_y.get() // 255

    UIBusy()

    """ ┌─────────────────┐
        │ Filtering image │
        └─────────────────┘ """
    result_image = filter(source_image, threshold_x, threshold_y, wrap_around=False, keep_alpha=True)

    # ↓ Preview result
    preview_data = list2bin(result_image, maxcolors, show_chessboard=True)
    preview_filtered = PhotoImage(data=preview_data)

    # ↓ Flagging as filtered
    view_src = False

    ShowPreview(preview_filtered, 'Result')

    # ↓ Binding switch on preview click
    zanyato.bind('<Button-1>', SwitchView)
    zanyato.bind('<ButtonRelease-1>', SwitchView)
    zanyato.bind('<space>', SwitchView)  # "Space" key. May be worth binding whole sortir?
    UINormal()
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
    sortir.update()


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
    sortir.update()


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
    sortir.update()


def zoomWheel(event) -> None:
    """zoomIn or zoomOut by mouse wheel."""

    if event.widget not in transparent_controls:
        if event.delta < 0:
            zoomOut()
        if event.delta > 0:
            zoomIn()


def SaveAsLinen() -> None:
    """Once pressed on Linen."""

    savefilename = asksaveasfilename(
        title='Save POV-Ray file',
        filetypes=[
            ('POV-Ray file', '.pov'),
            ('All Files', '*.*'),
        ],
        defaultextension='.pov',
        initialfile=Path(sourcefilename).stem + '_Linen.pov',
    )
    if savefilename == '':
        return

    """ ┌─────────────────────────────────────────────────────┐
        │ Converting list to POV and saving as "savefilename" │
        │ using global maxcolors, result_image                │
        └─────────────────────────────────────────────────────┘ """
    UIBusy()
    linen.linen(result_image, maxcolors, savefilename)
    UINormal()


def SaveAsStitch() -> None:
    """Once pressed on Stitch."""

    savefilename = asksaveasfilename(
        title='Save POV-Ray file',
        filetypes=[
            ('POV-Ray file', '.pov'),
            ('All Files', '*.*'),
        ],
        defaultextension='.pov',
        initialfile=Path(sourcefilename).stem + '_Stitch.pov',
    )
    if savefilename == '':
        return

    """ ┌─────────────────────────────────────────────────────┐
        │ Converting list to POV and saving as "savefilename" │
        │ using global maxcolors, result_image                │
        └─────────────────────────────────────────────────────┘ """
    UIBusy()
    stitch.stitch(result_image, maxcolors, savefilename)
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


""" ╒══════════════╕
    │ Initializing │
    ╰──────────────╯ """
product_name = 'POV-Ray Thread'
"""Program name."""
sourcefilename = ''
"""Name of file to be opened."""
zoom_factor = 0
"""Current zoom. Midpoint value 0 correspond to 1:1 zoom."""
view_src = True
"""Whether source image should be shown rather than the result."""
minizoom, maxizoom = (-4, 4)  # Zoom from 1:5 to 5:1
"""`minizoom` is a maximal zoom out + 1 (image looks `mini`),
   `maxizoom` is a maximal zoom in + 1 (image looks `maxi`)."""
threshold_increment = 1
"""Threshold increment for incWheel() and spinboxes."""

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
"""Help list(str) to be used for both main window and F1."""
help_str = '\n'.join(some_help)
"""Help str to be used for both main window and F1."""

""" ╔═══════════╗
    ║ Main body ║
    ╚═══════════╝ """
sortir = Tk()
"""Main dialog window."""
sortir.iconphoto(True, PhotoImage(data=b''.join(('P6\n3 16\n255\n'.encode(encoding='ascii'), randbytes(3 * 16 * 3)))))
sortir.title(product_name)

validate_entry = sortir.register(valiDig)

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
"""Buttons properties dictionary."""

# ↓ Info statuses dictionaries
info_normal = {'txt': f'{product_name} {__version__}', 'fg': 'grey', 'bg': 'grey90'}
info_busy = {'txt': 'BUSY, PLEASE WAIT', 'fg': 'red', 'bg': 'yellow'}

info_string = Label(
    sortir,
    text=info_normal['txt'],
    font=('courier', 7),
    foreground=info_normal['fg'],
    background=info_normal['bg'],
    relief='groove',
)
"""Info text label below main image, regularly updated."""
info_string.pack(side='bottom', padx=0, pady=(2, 0), fill='both')

""" ┌──────────────────────┐
    │ Top frame (controls) │
    └─────────────────────-┘ """
frame_top = Frame(sortir, borderwidth=2, relief='groove')
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
butt_file.pack(side='left', padx=(0, 10), pady=0, fill='both')

menu_file = Menu(butt_file, tearoff=False)
"""File menu."""
menu_file.add_command(label='Open...', state='normal', command=GetSource, accelerator='Ctrl+O')
menu_file.add_separator()
menu_file.add_command(label='Export Linen...', state='disabled', command=SaveAsLinen)
menu_file.add_command(label='Export Stitch...', state='disabled', command=SaveAsStitch)
menu_file.add_separator()
menu_file.add_command(label='Image Info...', accelerator='Ctrl+I', state='disabled', command=ShowInfo)
menu_file.add_separator()
menu_file.add_command(label='Help...', accelerator='F1', state='normal', command=ShowHelp)
menu_file.add_separator()
menu_file.add_command(label='Exit', state='normal', command=DisMiss, accelerator='Ctrl+Q')

butt_file['menu'] = menu_file  # Attach menu to menu button

butt_file.focus_set()  # Setting focus to "File..."

# ↓ Filter section begins
info_threshold = Label(frame_top, text='Filtering \nThreshold:', font=('helvetica', 8, 'italic'), justify='right', foreground='brown', state='disabled')
info_threshold.pack(side='left', padx=(0, 4), pady=0, fill='x')

# ↓ X-pass threshold control
info_threshold_x = Label(frame_top, text='X:', font=('helvetica', 10), state='disabled')
info_threshold_x.pack(side='left', padx=0, pady=0, fill='x')

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
spin_x.pack(side='left', padx=(0, 4), pady=0, fill='x')

# ↓ Y-pass threshold control
info_threshold_y = Label(frame_top, text='Y:', font=('helvetica', 10), state='disabled')
info_threshold_y.pack(side='left', padx=0, pady=0, fill='both')

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
spin_y.pack(side='left', padx=(0, 4), pady=0, fill='x')

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
butt_filter.pack(side='left', padx=0, pady=0, fill='both')

""" ┌──────────────────────────────┐
    │ Center frame (image preview) │
    └─────────────────────────────-┘ """
frame_preview = Frame(sortir, borderwidth=2, relief='groove')
"""Frame containing main label (image preview) and zoom control subframe."""
frame_preview.pack(side='top', anchor='center', expand=True)

canvas = Canvas(
    frame_preview,
    borderwidth=1,
    highlightthickness=1,
    # background='red',  # internal border
    # highlightbackground='green',  # external border
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
# ↓ "File..." mouseover
butt_file.bind('<Enter>', lambda event=None: butt_file.config(relief=butt['overrelief']))
butt_file.bind('<Leave>', lambda event=None: butt_file.config(relief=butt['relief']))
# ↓ Double-click image area to "Open..."
zanyato.bind('<Double-Button-1>', GetSource)
frame_preview.bind('<Double-Button-1>', GetSource)
# ↓ Whole sortir binding menu, "Open..." and "Exit"
sortir.bind_all('<Button-3>', ShowMenu)
sortir.bind_all('<Alt-f>', ShowMenu)
sortir.bind_all('<Alt-F>', ShowMenu)
sortir.bind_all('<F1>', ShowHelp)
sortir.bind_all('<Control-o>', GetSource)
sortir.bind_all('<Control-O>', GetSource)
sortir.bind_all('<Control-q>', DisMiss)
sortir.bind_all('<Control-Q>', DisMiss)
sortir.bind_all('<Control-w>', DisMiss)
sortir.bind_all('<Control-W>', DisMiss)

sortir.update()

# ↓ Readopting minsize
UIFit()
# ↓ Setting maxsize to fit 90% of screen
sortir.maxsize(9 * sortir.winfo_screenwidth() // 10, 9 * sortir.winfo_screenheight() // 10)
# ↓ Center window horizontally, +64 vertically
sortir.geometry(f'+{(sortir.winfo_screenwidth() - sortir.winfo_width()) // 2}+64')

sortir.mainloop()

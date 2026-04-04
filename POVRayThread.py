#!/usr/bin/env python3

"""
==============
POV-Ray Thread
==============
-------------------------------------------------------------------------
Converting image to canvas and cross stitch simulation in POV-Ray format.
-------------------------------------------------------------------------

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
# 1.28.6.8      UI have the potential to become standard.

__author__ = 'Ilya Razmanov'
__copyright__ = '(c) 2024-2026 Ilya Razmanov'
__credits__ = 'Ilya Razmanov'
__license__ = 'unlicense'
__version__ = '1.28.6.8'  # Main version № match that of export module
__maintainer__ = 'Ilya Razmanov'
__email__ = 'ilyarazmanov@gmail.com'
__status__ = 'Production'

from copy import deepcopy
from pathlib import Path
from random import randbytes  # Used for random icon only
from time import ctime  # Used to show file info only
from tkinter import Button, Frame, IntVar, Label, Menu, Menubutton, PhotoImage, Spinbox, TclError, Tk
from tkinter.filedialog import askopenfilename, asksaveasfilename
from tkinter.messagebox import showinfo

from pypng import png2list
from pypnm import list2bin, pnm2list

from export import linen, stitch
from filter.avgrow import filter

""" ╔══════════════════════════════════╗
    ║ GUI events and functions thereof ║
    ╚══════════════════════════════════╝ """


def DisMiss(event=None) -> None:
    """Kill dialog and continue."""

    sortir.destroy()


def ShowMenu(event) -> None:
    """Pop menu up (or sort of drop it down)."""

    menu02.post(event.x_root, event.y_root)


def ShowInfo(event=None) -> None:
    """Show image information."""

    file_size = Path(sourcefilename).stat().st_size
    file_size_str = f'{file_size / 1048576:.2f} Mb' if (file_size > 1048576) else f'{file_size / 1024:.2f} Kb' if (file_size > 1024) else f'{file_size} bytes'
    showinfo(
        title='Image information',
        message=f'File properties:\nLocation: {sourcefilename}\nSize: {file_size_str}\nLast modified: {ctime(Path(sourcefilename).stat().st_mtime)}',
        detail=f'Image properties, as represented internally:\nWidth: {X} px\nHeight: {Y} px\nChannels: {Z} channel{"s" if Z > 1 else ""}\nColor depth: {maxcolors + 1} gradations/channel',
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
    """Readopting minsize."""

    sortir.update()
    fit_width = min(sortir.winfo_reqwidth(), 9 * sortir.winfo_screenwidth() // 10)
    fit_height = min(sortir.winfo_reqheight(), 9 * sortir.winfo_screenheight() // 10)
    sortir.minsize(fit_width, fit_height)


def ShowPreview(preview_name: PhotoImage, caption: str) -> None:
    """Show preview_name PhotoImage with caption below."""

    global zoom_factor, preview

    preview = preview_name

    if zoom_factor > 0:
        preview = preview.zoom(
            zoom_factor + 1,
        )
        label_zoom['text'] = f'Zoom {zoom_factor + 1}:1'
    elif zoom_factor < 0:
        preview = preview.subsample(
            1 - zoom_factor,
        )
        label_zoom['text'] = f'Zoom 1:{1 - zoom_factor}'
    else:
        preview = preview_name
        label_zoom['text'] = 'Zoom 1:1'

    zanyato.config(text=caption, font=('helvetica', 8), image=preview, compound='top', padx=0, pady=0, justify='center', background=zanyato.master['background'], relief='flat', borderwidth=1, state='normal')


def GetSource(event=None) -> None:
    """Open source image and redefine other controls state."""

    global zoom_factor, view_src, info_normal
    global preview, preview_src, preview_filtered  # preview and copies of preview
    global sourcefilename, X, Y, Z, maxcolors, source_image, info
    global result_image  # deep copy of source_image to avoid cumulative filtering

    old_sourcefilename = sourcefilename  # Temporary saving info in case of "Open.." cancel
    sourcefilename = askopenfilename(title='Open image file', filetypes=[('Supported formats', '.png .ppm .pgm .pbm .pnm'), ('Portable network graphics', '.png'), ('Portable any map', '.ppm .pgm .pbm .pnm')])
    if sourcefilename == '':
        sourcefilename = old_sourcefilename
        return

    # ↓ Next must be set AFTER "sourcefilename", in case of "Open.." cancel
    zoom_factor = 0
    view_src = True

    UIBusy()

    if Path(sourcefilename).suffix.lower() == '.png':
        # ↓ Reading PNG image as list
        X, Y, Z, maxcolors, result_image, info = png2list(sourcefilename)

    elif Path(sourcefilename).suffix.lower() in ('.ppm', '.pgm', '.pbm', '.pnm'):
        # ↓ Reading PNM image as list
        X, Y, Z, maxcolors, result_image = pnm2list(sourcefilename)

    else:
        raise ValueError('Extension not recognized')

    """ ┌────────────────────────────────────────────┐
        │ Creating deep copy of source 3D list       │
        │ to avoid accumulating repetitive filtering │
        └────────────────────────────────────────────┘ """
    source_image = deepcopy(result_image)

    """ ┌───────────────┐
        │ Viewing image │
        └───────────────┘ """
    # ↓ Converting list to bytes of PPM-like structure "preview_data" in memory
    preview_data = list2bin(result_image, maxcolors, show_chessboard=True)
    # ↓ Now generating preview from "preview_data" bytes using Tkinter
    preview = PhotoImage(data=preview_data)
    # ↓ Finally the show part
    ShowPreview(preview, 'Source')

    """ ┌─────────────────────────────────────────────┐
        │ Creating copy of source preview for further │
        │ switch between source and result            │
        └─────────────────────────────────────────────┘ """
    preview_src = preview_filtered = preview

    # ↓ binding on preview click
    zanyato.bind('<Control-Button-1>', zoomIn)  # Ctrl + left click
    zanyato.bind('<Double-Control-Button-1>', zoomIn)  # Ctrl + left click too fast
    zanyato.bind('<Control-+>', zoomIn)
    zanyato.bind('<Control-=>', zoomIn)
    zanyato.bind('<Alt-Button-1>', zoomOut)  # Alt + left click
    zanyato.bind('<Double-Alt-Button-1>', zoomOut)  # Alt + left click too fast
    zanyato.bind('<Control-minus>', zoomOut)
    zanyato.bind('<Control-Key-1>', zoomOne)
    zanyato.bind('<Control-Alt-Key-0>', zoomOne)
    # ↓ binding global
    sortir.bind_all('<Return>', RunFilter)
    sortir.bind_all('<MouseWheel>', zoomWheel)  # Wheel scroll
    sortir.bind_all('<Control-i>', ShowInfo)
    menu02.entryconfig('Image Info...', state='normal')
    # ↓ enabling Save as...
    menu02.entryconfig('Export Linen...', state='normal')
    menu02.entryconfig('Export Stitch...', state='normal')

    # ↓ enabling zoom buttons
    butt_plus.config(state='normal', cursor='hand2')
    butt_minus.config(state='normal', cursor='hand2')
    # ↓ updating zoom label display
    label_zoom['text'] = 'Zoom 1:1'
    # ↓ Adding filename to window title a-la Photoshop
    sortir.title(f'{product_name}: {Path(sourcefilename).name}')
    info_normal = {'txt': f'{Path(sourcefilename).name} X={X} Y={Y} Z={Z} maxcolors={maxcolors}', 'fg': 'grey', 'bg': 'grey90'}
    # ↓ "Filter" mouseover
    butt_filter.bind('<Enter>', lambda event=None: butt_filter.config(foreground=butt['activeforeground'], background=butt['activebackground']))
    butt_filter.bind('<Leave>', lambda event=None: butt_filter.config(foreground=butt['foreground'], background=butt['background']))
    # ↓ Spinbox mouseovers
    spin01.bind('<Enter>', lambda event=None: spin01.config(foreground=butt['activeforeground'], background=butt['activebackground']))
    spin01.bind('<Leave>', lambda event=None: spin01.config(foreground=butt['foreground'], background='white'))
    spin02.bind('<Enter>', lambda event=None: spin02.config(foreground=butt['activeforeground'], background=butt['activebackground']))
    spin02.bind('<Leave>', lambda event=None: spin02.config(foreground=butt['foreground'], background='white'))
    # ↓ Spinbox scroll
    spin01.unbind('<MouseWheel>')
    spin01.bind('<MouseWheel>', incWheel)
    spin02.unbind('<MouseWheel>')
    spin02.bind('<MouseWheel>', incWheel)
    UINormal()
    UIFit()
    sortir.geometry(f'+{(sortir.winfo_screenwidth() - sortir.winfo_width()) // 2}+64')
    zanyato.focus_set()


def RunFilter(event=None) -> None:
    """Filter image, then preview result."""

    global zoom_factor, view_src
    global preview, preview_filtered
    global X, Y, Z, maxcolors, result_image, info

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
    threshold_x = maxcolors * int(spin01.get()) // 255  # Rescaling for 16-bit
    threshold_y = maxcolors * int(spin02.get()) // 255

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

    global zoom_factor, view_src, preview
    zoom_factor = min(zoom_factor + 1, 4)  # max zoom 5

    if view_src:
        ShowPreview(preview_src, 'Source')
    else:
        ShowPreview(preview_filtered, 'Result')

    # ↓ Reenabling +/- buttons
    butt_minus.config(state='normal', cursor='hand2')
    if zoom_factor == 4:  # max zoom 5
        butt_plus.config(state='disabled', cursor='arrow')
    else:
        butt_plus.config(state='normal', cursor='hand2')
    UIFit()
    sortir.update()


def zoomOut(event=None) -> None:
    """Zoom preview out."""

    global zoom_factor, view_src, preview
    zoom_factor = max(zoom_factor - 1, -4)  # min zoom 1/5

    if view_src:
        ShowPreview(preview_src, 'Source')
    else:
        ShowPreview(preview_filtered, 'Result')

    # ↓ Reenabling +/- buttons
    butt_plus.config(state='normal', cursor='hand2')
    if zoom_factor == -4:  # min zoom 1/5
        butt_minus.config(state='disabled', cursor='arrow')
    else:
        butt_minus.config(state='normal', cursor='hand2')
    UIFit()
    sortir.update()


def zoomOne(event=None) -> None:
    """Zoom 1:1."""

    global zoom_factor, view_src, preview
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


def SwitchView(event=None) -> None:
    """Switch preview between preview_src and preview_filtered."""

    global zoom_factor, view_src, preview
    view_src = not view_src
    if view_src:
        ShowPreview(preview_src, 'Source')
    else:
        ShowPreview(preview_filtered, 'Result')


def SaveAsLinen() -> None:
    """Once pressed on Linen."""

    global sourcefilename
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

    global sourcefilename
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
    if new_value.startswith('0') and int(new_value) != 0:
        return False  # leading zeroes lead to weird returns
    else:
        try:
            _ = int(new_value)
            if -1 < _ < 256:
                return True
            else:
                return False
        except ValueError:
            return False


def incWheel(event) -> None:
    """Increment or decrement spinboxes by mouse wheel."""

    if event.widget == spin01:
        if event.delta < 0:
            ini_threshold_x.set(min(255, max(0, ini_threshold_x.get() - 1)))
        if event.delta > 0:
            ini_threshold_x.set(min(255, max(0, ini_threshold_x.get() + 1)))
    if event.widget == spin02:
        if event.delta < 0:
            ini_threshold_y.set(min(255, max(0, ini_threshold_y.get() - 1)))
        if event.delta > 0:
            ini_threshold_y.set(min(255, max(0, ini_threshold_y.get() + 1)))


""" ╔═══════════╗
    ║ Main body ║
    ╚═══════════╝ """
# ↓ Initializing
sourcefilename = ''
zoom_factor = 0
view_src = True
product_name = 'POV-Ray Thread'

sortir = Tk()
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

# ↓ Info statuses dictionaries
info_normal = {'txt': f'{product_name} {__version__}', 'fg': 'grey', 'bg': 'grey90'}
info_busy = {'txt': 'BUSY, PLEASE WAIT', 'fg': 'red', 'bg': 'yellow'}

info_string = Label(sortir, text=info_normal['txt'], font=('courier', 7), foreground=info_normal['fg'], background=info_normal['bg'], relief='groove')
info_string.pack(side='bottom', padx=0, pady=(2, 0), fill='both')

frame_top = Frame(sortir, borderwidth=2, relief='groove')
frame_top.pack(side='top', anchor='w', pady=(0, 2))
frame_preview = Frame(sortir, borderwidth=2, relief='groove')
frame_preview.pack(side='top', anchor='center', expand=True)

""" ┌──────────────────────┐
    │ Top frame (controls) │
    └─────────────────────-┘ """

# ↓ File and menu
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
butt_file.pack(side='left', padx=(0, 10), pady=0, fill='both')

menu02 = Menu(butt_file, tearoff=False)  # "File" menu
menu02.add_command(label='Open...', state='normal', command=GetSource, accelerator='Ctrl+O')
menu02.add_separator()
menu02.add_command(label='Export Linen...', state='disabled', command=SaveAsLinen)
menu02.add_command(label='Export Stitch...', state='disabled', command=SaveAsStitch)
menu02.add_separator()
menu02.add_command(label='Image Info...', accelerator='Ctrl+I', state='disabled', command=ShowInfo)
menu02.add_separator()
menu02.add_command(label='Exit', state='normal', command=DisMiss, accelerator='Ctrl+Q')

butt_file['menu'] = menu02

butt_file.focus_set()  # Setting focus to "File..."

# ↓ Filter section begins
info00 = Label(frame_top, text='Filtering \nThreshold:', font=('helvetica', 8, 'italic'), justify='right', foreground='brown', state='disabled')
info00.pack(side='left', padx=(0, 4), pady=0, fill='x')

# ↓ X-pass threshold control
info01 = Label(frame_top, text='X:', font=('helvetica', 10), state='disabled')
info01.pack(side='left', padx=0, pady=0, fill='x')

ini_threshold_x = IntVar(value=16)
spin01 = Spinbox(
    frame_top,
    from_=0,
    to=255,
    increment=1,
    textvariable=ini_threshold_x,
    state='disabled',
    width=3,
    font=('helvetica', 11),
    validate='key',
    validatecommand=(validate_entry, '%P'),
)
spin01.pack(side='left', padx=(0, 4), pady=0, fill='x')

# ↓ Y-pass threshold control
info02 = Label(frame_top, text='Y:', font=('helvetica', 10), state='disabled')
info02.pack(side='left', padx=0, pady=0, fill='both')

ini_threshold_y = IntVar(value=8)
spin02 = Spinbox(
    frame_top,
    from_=0,
    to=255,
    increment=1,
    textvariable=ini_threshold_y,
    state='disabled',
    width=3,
    font=('helvetica', 11),
    validate='key',
    validatecommand=(validate_entry, '%P'),
)
spin02.pack(side='left', padx=(0, 4), pady=0, fill='x')

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
butt_filter.pack(side='left', padx=0, pady=0, fill='both')

""" ┌──────────────────────────────┐
    │ Center frame (image preview) │
    └─────────────────────────────-┘ """
zanyato = Label(
    frame_preview,
    text='Preview area.\n  Double click to open image,\n  Right click or Alt+F for a menu.\nWith image opened,\n  Ctrl+Click to zoom in,\n  Alt+Click to zoom out,\n  Enter to filter.\nWhen filtered, click or Space bar\nto switch source/result.',
    font=('helvetica', 12),
    justify='left',
    borderwidth=2,
    padx=24,
    pady=24,
    background='grey90',
    relief='groove',
)

frame_zoom = Frame(frame_preview, width=300, borderwidth=2, relief='groove')
frame_zoom.pack(side='bottom')

butt_plus = Button(frame_zoom, text='+', font=('courier', 8), width=2, cursor='arrow', state='disabled', borderwidth=1, command=zoomIn)
butt_plus.pack(side='left', padx=0, pady=0, fill='both')

butt_minus = Button(frame_zoom, text='-', font=('courier', 8), width=2, cursor='arrow', state='disabled', borderwidth=1, command=zoomOut)
butt_minus.pack(side='right', padx=0, pady=0, fill='both')

label_zoom = Label(frame_zoom, text='Zoom 1:1', font=('courier', 8), state='disabled')
label_zoom.pack(side='left', anchor='n', padx=2, pady=0, fill='both')

transparent_controls = (spin01, spin02)  # To be cut off global evens

""" ┌─────────────────────────────────────────────┐
    │ Binding everything that does not need image │
    └────────────────────────────────────────────-┘ """
# ↓ "File..." mouseover
butt_file.bind('<Enter>', lambda event=None: butt_file.config(relief=butt['overrelief']))
butt_file.bind('<Leave>', lambda event=None: butt_file.config(relief=butt['relief']))
# ↓ Double-click image area to "Open..."
zanyato.bind('<Double-Button-1>', GetSource)
frame_preview.bind('<Double-Button-1>', GetSource)
zanyato.pack(side='top')
# ↓ Whole sortir binding menu, "Open..." and "Exit"
sortir.bind_all('<Button-3>', ShowMenu)
sortir.bind_all('<Alt-f>', ShowMenu)
sortir.bind_all('<Control-q>', DisMiss)
sortir.bind_all('<Control-Q>', DisMiss)
sortir.bind_all('<Control-w>', DisMiss)
sortir.bind_all('<Control-W>', DisMiss)

# ↓ Center window horizontally, +100 vertically
sortir.update()
# print(sortir.winfo_width(), sortir.winfo_height())
# ↓ Readopting minsize
UIFit()
# ↓ Setting maxsize to fit 90% of screen
sortir.maxsize(9 * sortir.winfo_screenwidth() // 10, 9 * sortir.winfo_screenheight() // 10)
sortir.geometry(f'+{(sortir.winfo_screenwidth() - sortir.winfo_width()) // 2}+64')

sortir.mainloop()

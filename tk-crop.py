#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Based on https://github.com/dnouri/photo_splitter
'''

BATCH_PROGNAME = 'Tk-crop-BATCH'
CROPPER_PROGNAME = 'Tk-crop-CROPPER'
VERSION = '0.0.1'

import os
import sys
from PIL import Image, ImageTk, ImageFilter, ImageChops

# for Python3
import tkinter as tk
from tkinter import filedialog as tkfd

FIXED_CROPS = [
    ('A', {'height_px': 200, 'width_px': 200, 'color': 'blue'}),
    ('B', {'height_px': 500, 'width_px': 500, 'color': 'yellow'}),
    ('C', {'height_px': 600, 'width_px': 1200, 'color': 'magenta'}),
    ('D', {'height_px': 720, 'width_px': 1280, 'color': 'red'}),
]

thumbsize = 1024, 1024
thumboffset = 16


class BatchApplication(tk.Frame):
    def __init__(self, master=None):
        tk.Frame.__init__(self, master)
        self.grid()
        self.createWidgets()

        foldername = tkfd.askdirectory(master=self, parent=self, mustexist=True,
                      title=('Select folder containing images'))

        self.image_folder = foldername

        self.descrText.insert(1.0, f"Launching croppers for images in folder:\n\n\t{self.image_folder}")
        self.descrText.update()

    def launchCroppers(self):
        for i, imgfile_base in enumerate(os.listdir(self.image_folder)):
            if imgfile_base == '.DS_Store':
                continue
            imgfile = os.path.join(self.image_folder, imgfile_base)
            if os.path.isfile(imgfile) and not imgfile_base.startswith('tk_crop__'):
                try:
                    crop_app = CropApplication(filename=imgfile)
                    crop_app.title(f"{CROPPER_PROGNAME}-{imgfile}")
                except ValueError as e:
                    #print(f"Error: {e}")
                    self.errorText.insert(float(i+1), f"Error: {e}\n")
                    self.errorText.update()
                    continue

    def createWidgets(self):
        self.canvas = tk.Canvas(
            self, height=1, width=1, relief=tk.SUNKEN)

        self.workFrame = tk.LabelFrame(self)

        self.ActionFrame = tk.LabelFrame(self, text='Action')

        self.descrText = tk.Text(self.ActionFrame, height=5, width=50)
        self.errorText = tk.Text(self.ActionFrame, height=5, width=50)

        self.goButton = tk.Button(self.ActionFrame, text='Batch crop',
                                       activebackground='#0F0', command=self.launchCroppers)

        self.quitButton = tk.Button(self.ActionFrame, text='Quit',
                                         activebackground='#F00', command=self.quit)

        self.descrText.grid(row=0, column=2)
        self.errorText.grid(row=1, column=2)
        self.goButton.grid(row=2, column=2)
        self.quitButton.grid(row=2, column=4)

        self.canvas.grid(row=0, columnspan=3)
        self.workFrame.grid(row=1, column=1)
        self.ActionFrame.grid(row=0, column=0)


class CropApplication(tk.Toplevel):
    def __init__(self, filename, scale=0.):
        # max crop height
        self.max_height_px = max(FIXED_CROPS, key=lambda x: x[1]['height_px'])[1]['height_px']
        self.max_width_px = max(FIXED_CROPS, key=lambda x: x[1]['width_px'])[1]['width_px']

        tk.Toplevel.__init__(self)
        self.grid()
        self.createWidgets()
        self.selected_croprect_id = None

        # fixed 4 sizes of crop rectangle
        self.n = len(FIXED_CROPS)
        self.crop_rects = [Rect((0, 0), (tup[1]["width_px"], tup[1]["height_px"])) for tup in FIXED_CROPS]
        self.crop_rect_colors = [tup[1]['color'] for tup in FIXED_CROPS]
        self.crop_rect_names = [tup[0] for tup in FIXED_CROPS]
        self.canvas_rects = [None]*self.n

        self.region_rect = []
        self.w = 1
        self.h = 1
        self.x0 = 0
        self.y0 = 0
        self.scale = None

        self.image_scale = scale
        self.filename = filename
        self.loadimage(px_scale=(1.0 + 0.1*scale))

    def createWidgets(self):
        self.canvas = tk.Canvas(
            self, height=1, width=1, relief=tk.SUNKEN)

        # click
        self.canvas.bind('<Button-1>', self.canvas_mouse1_callback)
        # drag
        self.canvas.bind('<B1-Motion>', self.canvas_mouseb1move_callback)
        # release
        self.canvas.bind('<ButtonRelease-1>', self.canvas_mouseup1_callback)

        self.workFrame = tk.LabelFrame(self)

        self.ActionFrame = tk.LabelFrame(self, text='Action')

        self.plusButton = tk.Button(self.ActionFrame, text='+',
                                       activebackground='#0F0', command=self.enlargen_image)

        self.minusButton = tk.Button(self.ActionFrame, text='-',
                                       activebackground='#0F0', command=self.ensmallen_image)

        self.goButton = tk.Button(self.ActionFrame, text='Crop and save',
                                       activebackground='#0F0', command=self.start_cropping)

        self.closeButton = tk.Button(self.ActionFrame, text='Close',
                                         activebackground='#F00', command=self.destroy)

        self.plusButton.grid(row=0, column=1)
        self.minusButton.grid(row=0, column=2)

        self.goButton.grid(row=0, column=3)
        self.closeButton.grid(row=0, column=4)

        self.canvas.grid(row=0, columnspan=3)
        self.workFrame.grid(row=1, column=1)
        self.ActionFrame.grid(row=1, column=2)

    def set_button_state(self):
        if self.n > 0:
            self.goButton.config(state = 'normal')
        else:
            self.goButton.config(state = 'disabled')

    def canvas_mouse1_callback(self, event):
        try:
            selected_croprect_id = self.canvas.find_withtag("current")[0]
            if selected_croprect_id == 1:
                # main image, not allowed to move it
                return
            self.selected_croprect_id = selected_croprect_id
        except IndexError as e:
            print(e)
            pass

    def get_current_croprect_coords(self):
        return self.canvas.bbox(self.selected_croprect_id)

    def canvas_mouseb1move_callback(self, event, adjust=False):
        if self.selected_croprect_id is not None:
            curr_coords = self.get_current_croprect_coords()
            leftlim = self.left_limit
            rightlim = self.right_limit-(curr_coords[2]-curr_coords[0])
            bottomlim = self.bottom_limit
            toplim = self.top_limit-(curr_coords[3]-curr_coords[1])

            x_motion = event.x
            y_motion = event.y

            if adjust:
                if x_motion < leftlim:
                    x_motion = leftlim
                elif x_motion > rightlim:
                    x_motion = rightlim

                if y_motion < bottomlim:
                    y_motion = bottomlim
                elif y_motion > toplim:
                    y_motion = toplim

            self.canvas.moveto(self.selected_croprect_id, x_motion, y_motion)

    def ensmallen_image(self):
        new_scale = int(self.image_scale-1)
        crop_app = CropApplication(filename=self.filename, scale=new_scale)

        if new_scale < 0:
            crop_app.title(f"{CROPPER_PROGNAME}-{self.filename}-smaller-{-new_scale}")
        else:
            crop_app.title(f"{CROPPER_PROGNAME}-{self.filename}-larger-{new_scale}")
        self.destroy()

    def enlargen_image(self):
        new_scale = int(self.image_scale+1)
        crop_app = CropApplication(filename=self.filename, scale=new_scale)
        if new_scale < 0:
            crop_app.title(f"{CROPPER_PROGNAME}-{self.filename}-smaller-{-new_scale}")
        else:
            crop_app.title(f"{CROPPER_PROGNAME}-{self.filename}-larger-{new_scale}")
        self.destroy()

    def canvas_mouseup1_callback(self, event):
        self.canvas_mouseb1move_callback(event, adjust=True)
        self.selected_croprect_id = None

    def redraw_rect(self):
        for i, (croparea, cropcolor) in enumerate(zip(self.crop_rects, self.crop_rect_colors)):
            self.drawrect(croparea.rescale_rect(self.scale, self.x0, self.y0), cropcolor, i)

    def drawrect(self, rect, color, index):
        bbox = (rect.left, rect.top, rect.right, rect.bottom)
        cr = self.canvas.create_rectangle(
            bbox, activefill='', stipple='gray25', outline=color, width=2)
        self.canvas_rects[index] = cr

    def displayimage(self):
        rr = (self.region_rect.left, self.region_rect.top, self.region_rect.right, self.region_rect.bottom)
        self.image_thumb = self.image.crop(rr)
        self.image_thumb.thumbnail(thumbsize, Image.LANCZOS)

        self.image_thumb_rect = Rect(self.image_thumb.size)

        self.photoimage = ImageTk.PhotoImage(self.image_thumb)
        w, h = self.image_thumb.size
        self.canvas.configure(
            width=(w + 2 * thumboffset),
            height=(h + 2 * thumboffset))

        self.canv_img = self.canvas.create_image(
            thumboffset,
            thumboffset,
            anchor=tk.NW,
            image=self.photoimage)

        self.left_limit = thumboffset
        self.bottom_limit = thumboffset
        # account for the `moveto` method moving the top-left corner of the rectangle
        self.right_limit = w + thumboffset
        self.top_limit = h + thumboffset

        x_scale = float(self.region_rect.w) / self.image_thumb_rect.w
        y_scale = float(self.region_rect.h) / self.image_thumb_rect.h
        self.scale = (x_scale, y_scale)
        self.redraw_rect()
        self.set_button_state()

    def loadimage(self, px_scale=1.0):
        image = Image.open(self.filename)

        if px_scale != 1.0:
            w_curr = image.size[0]
            h_curr = image.size[1]

            w_new = int(w_curr*px_scale)
            h_new = int(h_curr*px_scale)

            self.image = image.resize((w_new, h_new), resample=Image.LANCZOS)
        else:
            self.image = image

        self.image_rect = Rect(self.image.size)
        self.w = self.image_rect.w
        self.h = self.image_rect.h
        self.region_rect = Rect((0, 0), (self.w, self.h))

        self.displayimage()

    def newfilename(self, filenum):
        f, ext = os.path.splitext(self.filename)
        f = os.path.basename(f)
        parent = os.path.dirname(self.filename)
        # use fixed crop name (A/B/C/D) vs. number
        formatName = self.crop_rect_names[filenum-1]

        if self.image_scale == 0:
            fullPath = os.path.join(parent, f"tk_crop__{formatName}__{f}{ext}")
        else:
            if self.image_scale < 0:
                fullPath = os.path.join(parent, f"tk_crop__{formatName}__{f}_SMALLER_{self.image_scale}{ext}")
            else:
                fullPath = os.path.join(parent, f"tk_crop__{formatName}__{f}_LARGER_{self.image_scale}{ext}")
        return fullPath

    def start_cropping(self):
        cropcount = 0
        for i, croparea in enumerate(self.crop_rects):
            cropcount += 1
            f = self.newfilename(cropcount)
            print(f"new filename: {f}")
            moved_coords = self.canvas.coords(self.canvas_rects[i])
            moved_croparea = Rect((moved_coords[0], moved_coords[1]), (moved_coords[2], moved_coords[3]))
            scaled_croparea = moved_croparea.scale_rect(self.scale)

            actual_width = scaled_croparea.w
            actual_height = scaled_croparea.h
            desired_width = croparea.w
            desired_height = croparea.h

            scaled_croparea.set_points((scaled_croparea.left, scaled_croparea.top), (scaled_croparea.left+desired_width, scaled_croparea.top+desired_height))

            self.crop(scaled_croparea, f)

    def crop(self, croparea, filename):
        ca = (croparea.left, croparea.top, croparea.right, croparea.bottom)
        newimg = self.image.crop(ca)
        newimg.save(filename)


class Rect(object):
    def __init__(self, *args):
        self.set_points(*args)

    def set_points(self, *args):
        if len(args) == 2:
            pt1 = args[0]
            pt2 = args[1]
        elif len(args) == 1:
            pt1 = (0, 0)
            pt2 = args[0]
        elif len(args) == 0:
            pt1 = (0, 0)
            pt2 = (0, 0)

        x1, y1 = pt1
        x2, y2 = pt2

        self.left = min(x1, x2)
        self.top = min(y1, y2)
        self.right = max(x1, x2)
        self.bottom = max(y1, y2)

        self._update_dims()

    def _update_dims(self):
        """added to provide w and h dimensions."""

        self.w = self.right - self.left
        self.h = self.bottom - self.top

    def scale_rect(self, scale):
        x_scale = scale[0]
        y_scale = scale[1]

        r = Rect()
        r.top = int((self.top - thumboffset) * y_scale + 0.5)
        r.bottom = int((self.bottom - thumboffset) * y_scale + 0.5)
        r.right = int((self.right - thumboffset) * x_scale + 0.5)
        r.left = int((self.left - thumboffset) * x_scale + 0.5)
        r._update_dims()

        return r

    def rescale_rect(self, scale, x0, y0):
        x_scale = scale[0]
        y_scale = scale[1]

        r = Rect()
        r.top = int((self.top - y0) / y_scale + thumboffset)
        r.bottom = int((self.bottom - y0) / y_scale + thumboffset)
        r.right = int((self.right - x0) / x_scale + thumboffset)
        r.left = int((self.left - x0) / x_scale + thumboffset)
        r._update_dims()

        return r

    def __repr__(self):
        return '(%d,%d)-(%d,%d)' % (self.left,
                                    self.top, self.right, self.bottom)


def main():
    dl_app = BatchApplication()
    dl_app.master.title(BATCH_PROGNAME)
    dl_app.mainloop()


if __name__ == '__main__':
    main()

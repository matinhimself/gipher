import operator
from functools import reduce

from PIL import Image, ImageSequence
from collections import OrderedDict
import imageio as iio
import numpy
from typing import List, Tuple


class Timeline:
    class Frame:
        def __init__(self, image, layer: int, position: Tuple = (0, 0), **kwargs):
            self.size = kwargs.pop('size', image.size)
            if ratio := kwargs.pop('ratio', None):
                self.size = (int(self.size[0] * ratio), int(self.size[1] * ratio))
            self.position = position
            self.image = image.resize(self.size, Image.ANTIALIAS)
            self.layer = layer
            self._from = kwargs.pop('from', 0)
            self._to = kwargs.pop('to', -1)

        def is_time(self, t: int):
            return self._from < t and (self._to >= t or
                                       self._to == -1)

        def __str__(self):
            return f"static image layer:{self.layer}"

        def __repr__(self):
            return self.__str__()

    class DynamicFrame(Frame):
        def __init__(self, image, duration: int, layer: int, t: int, position: Tuple = (0, 0), **kwargs):
            self.time = t
            self.duration = duration
            self._from = kwargs.pop('from', 0)
            self._to = kwargs.pop('from', -1)
            super().__init__(image, layer, position, **kwargs)

        def __str__(self):
            return f"dynamic frame layer:{self.layer}, from:{self.time}, for:{self.duration}"

        def __repr__(self):
            return self.__str__()

    def __init__(self, trim_base=True):
        # Trim base will assure that composed gif
        # will finish as soon as layer 0 duration finishes
        self.trim_base = trim_base
        self._layer_counter = 0
        self._remaining_frames: List[Timeline.DynamicFrame] = []
        self._max_duration = 0
        self._static_frames: List[Timeline.Frame] = []
        self._max_time = -1
        self.timeline = OrderedDict()

    def _add(self, f: DynamicFrame):
        t = f.time

        if t in self.timeline:
            self.timeline[t].append(f)
            return

        self.timeline[t] = [f]

    def __iter__(self):
        return iter(self.timeline.items())

    def add_image(self, filepath: str, **kwargs):
        """
        :param filepath:
        :param kwargs:
        :return:
        :Keyword Arguments:
            * *size* (``Tuple``) --
                change size of frames
            * *ratio* (``int``) --
                ratio of size
            * *layer* (``int``) --
                change order of layers
            * *position* (``Tuple``) --
                position of frame


            # Todo:
                fade
                loop
                from_time
                to_time
                from_time
                from_time
        """
        is_base_layer = self._layer_counter == 0 and self.trim_base
        from_ = kwargs.pop('from', 0)
        if from_ > 0 and is_base_layer:
            raise Exception("can't use image layer as base layer `from` is not 0.")

        to = kwargs.pop('to', -1)
        if to == -1 and is_base_layer:
            raise Exception("can't use image layer as base layer when `to` is not provided.")

        layer = kwargs.pop('layer', self._layer_counter)
        self._layer_counter = max(layer + 1, self._layer_counter + 1)

        img = Image.open(filepath)

        self._static_frames.append(Timeline.Frame(img, layer, from_=from_, to=to, **kwargs))

    def add_gif(self, filepath: str, **kwargs):
        """
        :param filepath:
        :param kwargs:
        :return:
        :Keyword Arguments:
            * *size* (``Tuple``) --
                change size of frames
            * *ratio* (``int``) --
                ratio of size
            * *layer* (``int``) --
                change order of layers
            * *position* (``Tuple``) --
                position of frame

                            is_main

            # Todo:
                fade
                loop
                from_time
                to_time
                from_time
                from_time
        """
        loop = kwargs.pop('loop', False)

        is_base_layer = self._layer_counter == 0 and self.trim_base
        layer = kwargs.pop('layer', self._layer_counter)
        self._layer_counter = max(layer + 1, self._layer_counter + 1)

        gif = Image.open(filepath)

        # can use final t but we need it for adding loops
        gif_duration = reduce(operator.add, [img.info['duration'] for img in ImageSequence.Iterator(gif)])

        from_ = kwargs.pop('from', 0)
        t = from_
        to = kwargs.pop('to', -1)
        if to == -1 and is_base_layer and loop:
            raise Exception("can't use loop layer as base layer when `to` is not provided.")

        for img in ImageSequence.Iterator(gif):
            dur = img.info['duration']
            if t > to != -1 or t > self._max_time != -1:
                break

            img_copy = img.copy()
            self._add(Timeline.DynamicFrame(img_copy, dur, layer, t, _from=from_, _to=to, **kwargs))
            if loop:
                for i in range(t + gif_duration, self._max_time, gif_duration):
                    self._add(Timeline.DynamicFrame(img_copy, dur, layer, i, _from=from_, _to=to, **kwargs))

            t += dur

        self._max_time = gif_duration if is_base_layer else self._max_time
        self._max_duration = max(self._max_duration, gif_duration)

    def save(self, filepath: str):
        times = sorted(list(self.timeline.keys()))
        times.append(self._max_duration)
        durations = list(map(lambda x, y: (x - y) / 1000, times[1:], times[:-1]))

        self._expand_frames()
        with iio.get_writer(filepath, mode='I', duration=durations) as writer:
            for time, bucket in self.timeline.items():
                b = sorted(bucket + self._static_frames, key=lambda x: x.layer)
                background = b[0].image.convert('RGBA')
                for foreground in b[1:]:
                    if type(foreground) is Timeline.Frame and not foreground.is_time(time):
                        continue
                    background.paste(foreground.image.convert('RGBA'), foreground.position,
                                     foreground.image.convert('RGBA'))
                writer.append_data(numpy.array(background))

    def _expand_frames(self):
        length = len(self.timeline)
        self.timeline = dict(sorted(self.timeline.items(), key=lambda item: item[0]))
        key_list = sorted(self.timeline.keys())
        for i in range(length - 1):
            for frame in self.timeline[key_list[i]]:
                if frame.time + frame.duration > key_list[i + 1]:
                    self.timeline[key_list[i + 1]].append(frame)

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

        def __str__(self):
            return f"static image layer:{self.layer}"

        def __repr__(self):
            return self.__str__()

    class DynamicFrame(Frame):
        def __init__(self, image, duration: int, layer: int, t: int, position: Tuple = (0, 0), **kwargs):
            self.time = t
            self.duration = duration
            super().__init__(image, layer, position, **kwargs)

        def __str__(self):
            return f"dynamic frame layer:{self.layer}, from:{self.time}, for:{self.duration}"

        def __repr__(self):
            return self.__str__()

    def __init__(self):
        self._layer_counter = 0
        self._remaining_frames: List[Timeline.DynamicFrame] = []
        self._max_duration = 0
        self._static_frames: List[Timeline.Frame] = []
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
        """
        layer = kwargs.pop('layer', self._layer_counter)
        self._layer_counter = max(layer + 1, self._layer_counter + 1)

        img = Image.open(filepath)

        self._static_frames.append(Timeline.Frame(img, layer, **kwargs))

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
        """
        layer = kwargs.pop('layer', self._layer_counter)
        self._layer_counter = max(layer + 1, self._layer_counter + 1)

        gif = Image.open(filepath)
        t = 0
        for img in ImageSequence.Iterator(gif):
            dur = img.info['duration']
            self._add(Timeline.DynamicFrame(img.copy(), dur, layer, t, **kwargs))
            t += dur
        self._max_duration = max(self._max_duration, t)

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

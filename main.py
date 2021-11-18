import re

from gifer import Timeline


def files_to_gif(*args, result_file_path='./result.gif'):
    frames = Timeline()
    for f in args:
        if re.match(".*.gif", f):
            frames.add_gif(f)
        elif re.match(".*.png", f):
            frames.add_image(f)
    frames.save(result_file_path)


def files_to_gif_with_meta(*args, result_file_path='./result2.gif'):
    """
    :Arguments:
        * `Sample` *
        {
            'file_path': '/path/to/file.gif',
            'layer': 0,
            'size' :(100, 100),
            'position': (20,20)
        }
    """
    frames = Timeline()
    for arg in args:
        f = arg.pop('file_path')

        kwargs = {}
        for key in arg:
            kwargs[key] = arg[key]

        if re.match(".*.gif", f):
            frames.add_gif(f, **kwargs)
        elif re.match(".*.png", f):
            frames.add_image(f, **kwargs)
    frames.save(result_file_path)


if __name__ == '__main__':

    # will compose gif
    files_to_gif("./samples/1.gif", "./samples/2.gif", "./samples/2.gif", "./samples/5.gif", "./samples/logo.png")

    files_to_gif_with_meta(
        {
            'file_path': './samples/1.gif',
        },
        {
            'file_path': './samples/2.gif',
            'size': (100, 100),
            'position': (300, 300)
        },
        {
            'file_path': './samples/4.gif',
            'size': (100, 100),
            'layer': 3,
            'position': (20, 20)
        },
        {
            'file_path': './samples/5.gif',
            'size': (40, 40),
            'layer': 2,
            'position': (70, 50)
        },
        {
            'file_path': './samples/logo.png',
            'ratio': 0.2,
            'position': (350, 20)
        },

    )
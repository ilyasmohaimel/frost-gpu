"""Continue the saved model without rebuilding or changing its camera path."""
import os
import time
import bpy

scene = bpy.context.scene
scene.frame_start = int(os.environ['FROST_FRAME_START'])
scene.frame_end = int(os.environ['FROST_FRAME_END'])


def cool_between_frames(_scene):
    time.sleep(float(os.environ.get('FROST_FRAME_PAUSE', '3')))


bpy.app.handlers.render_write.append(cool_between_frames)
bpy.ops.render.render(animation=True)

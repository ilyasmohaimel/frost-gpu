import bpy,math,json,pathlib,sys
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
import os
private=pathlib.Path(os.environ.get('FROST_FILM_CACHE',str(pathlib.Path.home()/'.local/share/frost-gpu-film')));work=pathlib.Path(__file__).resolve().parent;comp=work.parent/'composition';out=comp/'assets/blender';out.mkdir(parents=True,exist_ok=True)
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [];mode=args[0] if args else 'product-proof'
bpy.ops.wm.read_factory_settings(use_empty=True);scene=bpy.context.scene
scene.render.engine='BLENDER_EEVEE_NEXT';scene.eevee.taa_render_samples=64;scene.eevee.use_raytracing=True
scene.render.resolution_x=1920;scene.render.resolution_y=1080;scene.render.resolution_percentage=100;scene.render.fps=30;scene.render.image_settings.file_format='PNG'
scene.world=bpy.data.worlds.new('Silver studio');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.14,.17,.22,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.2
scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast'
def mat(name,c,metal=0,rough=.45,emission=0):
 m=bpy.data.materials.new(name);m.use_nodes=True;n=m.node_tree.nodes.get('Principled BSDF');n.inputs['Base Color'].default_value=(*c,1);n.inputs['Metallic'].default_value=metal;n.inputs['Roughness'].default_value=rough
 if emission:n.inputs['Emission Color'].default_value=(*c,1);n.inputs['Emission Strength'].default_value=emission
 return m
def box(name,loc,size,material,bevel=.001):
 bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.name=name;o.dimensions=size;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(material)
 if bevel:q=o.modifiers.new('Manufactured edge','BEVEL');q.width=bevel;q.segments=3;o.modifiers.new('Surface normals','WEIGHTED_NORMAL')
 return o
def apply_modifiers(o):
 bpy.context.view_layer.objects.active=o
 for m in list(o.modifiers):bpy.ops.object.modifier_apply(modifier=m.name)
def boolean_cut(target,tool):
 bpy.context.view_layer.objects.active=target;m=target.modifiers.new('Section','BOOLEAN');m.operation='DIFFERENCE';m.solver='EXACT';m.object=tool;bpy.ops.object.modifier_apply(modifier=m.name)
def xpx(x):return (x-800)*.0006
def ypx(y):return .205-(y-430)*(.463/685)
black=mat('Graphite enclosure',(.008,.011,.016),.08,.45);rubber=mat('Soft black rubber',(.003,.004,.006),0,.75);red=mat('Red armour cap',(.42,.006,.016),.12,.38)
source_image=bpy.data.images.load(str(private/'online-reference/asus-top-hires.png'))
# The official product reference supplies the exact legends and deck pattern as a calibrated model material.
# It is never a photographic shot in the edit. Personal photographs are reference only.
def reference_material(name,strength):
 m=bpy.data.materials.new(name);m.use_nodes=True;n=m.node_tree.nodes.get('Principled BSDF');n.inputs['Roughness'].default_value=.5
 tex=m.node_tree.nodes.new('ShaderNodeTexImage');tex.image=source_image;tex.interpolation='Linear';m.node_tree.links.new(tex.outputs['Color'],n.inputs['Base Color']);m.node_tree.links.new(tex.outputs['Color'],n.inputs['Emission Color'])
 sep=m.node_tree.nodes.new('ShaderNodeSeparateColor');sep.mode='HSV';m.node_tree.links.new(tex.outputs['Color'],sep.inputs['Color']);mul=m.node_tree.nodes.new('ShaderNodeMath');mul.operation='MULTIPLY';mul.inputs[1].default_value=strength;m.node_tree.links.new(sep.outputs[1],mul.inputs[0]);m.node_tree.links.new(mul.outputs[0],n.inputs['Emission Strength']);return m
surface=reference_material('Calibrated G513QY deck',.14);key_surface=reference_material('Exact G513QY legends and RGB borders',.75)
def projected_uv(o,top_only=True):
 o.data.materials.clear();o.data.materials.append(surface if o.name=='G513 deck' else key_surface);o.data.materials.append(black);uv=o.data.uv_layers.new(name='Reference calibration');o.data.uv_layers.active=uv;uv.active_render=True
 for poly in o.data.polygons:
  poly.material_index=0 if poly.normal.z>.5 or not top_only else 1
  for loop_index in poly.loop_indices:
   v=o.matrix_world@o.data.vertices[o.data.loops[loop_index].vertex_index].co
   px=v.x/.0006+800;py=430+(.205-v.y)/(.463/685);uv.data[loop_index].uv=(px/1600,1-py/1176)
# New enclosure replaces the donor mesh: no number-pad well, side USB holes or old power button remain.
# A shallow front undercut replaces the generic vertical slab profile.
profile=[(-.258,.037),(.205,.037),(.205,.003),(-.205,.003),(-.258,.019)]
verts=[(x,y,z) for x in [-.321,.321] for y,z in profile];count=len(profile)
faces=[tuple(range(count-1,-1,-1)),tuple(range(count,count*2))]+[(i,(i+1)%count,(i+1)%count+count,i+count) for i in range(count)]
mesh=bpy.data.meshes.new('Tapered shell');mesh.from_pydata(verts,[],faces);mesh.update();body=bpy.data.objects.new('G513 enclosure',mesh);scene.collection.objects.link(body);mesh.materials.append(black)
q=body.modifiers.new('Rounded shell edge','BEVEL');q.width=.0035;q.segments=3;body.modifiers.new('Shell normals','WEIGHTED_NORMAL');apply_modifiers(body)
deck=box('G513 deck',(0,-.0265,.0372),(.6336,.457,.0014),surface,.004);apply_modifiers(deck);projected_uv(deck)
# Recessed single clickpad, centred and sized directly from the master reference.
pad=box('Integrated clickpad',(xpx(800),ypx(970.5),.0382),((994-606)*.0006,(1085-856)*(.463/685),.0012),surface,.002);apply_modifiers(pad);projected_uv(pad)
keys=[]
def polygon_cap(name,poly,z=.0393):
 pts=[(xpx(x),ypx(y)) for x,y in poly]
 area=sum(pts[i][0]*pts[(i+1)%len(pts)][1]-pts[(i+1)%len(pts)][0]*pts[i][1] for i in range(len(pts)))
 if area<0:pts.reverse()
 n=len(pts);verts=[(x,y,z-.0012) for x,y in pts]+[(x,y,z+.0012) for x,y in pts];faces=[tuple(range(n-1,-1,-1)),tuple(range(n,n*2))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
 mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update();o=bpy.data.objects.new(name,mesh);scene.collection.objects.link(o);projected_uv(o);q=o.modifiers.new('Low profile cap edge','BEVEL');q.width=.00025;q.segments=2;q.material=1;o.modifiers.new('Keycap normals','WEIGHTED_NORMAL');return o
shapes=json.loads((work/'traced-keys.json').read_text())
for i,k in enumerate(shapes):
 o=polygon_cap('Reference key '+str(i),k['polygon']);keys.append(o)
power=polygon_cap('Recessed power button',[[1211,459],[1232,459],[1240,473],[1238,490],[1206,490],[1204,473]])
# Hinges, armour cap and perforated cooling strip match the reference silhouette.
for x in [-.292,.292]:box('Display hinge',(x,.194,.054),(.025,.03,.035),black,.003)
box('Rear cooling strip',(0,.199,.044),(.636,.025,.012),black,.002)
box('Red armour cap',(-.197,.199,.045),(.244,.026,.013),red,.002)
for i in range(59):
 x=-.305+i*.0105
 box('Rear cooling groove '+str(i),(x,.192,.044),(.003,.003,.009),rubber,.0004)
# G513QY right side has a cooling vent. Ports are on the left and rear.
for side in [-1,1]:
 tool=box('Vent cutter',(side*.318,.124,.020),(.018,.135,.017),rubber,0);boolean_cut(body,tool);bpy.data.objects.remove(tool,do_unlink=True)
 box('Vent shadow',(side*.313,.124,.02),(.002,.132,.015),rubber,0)
 for i in range(23):
  o=box('Vent louver',(side*.32,.061+i*.0057,.020),(.004,.0018,.016),black,.0004);o.rotation_euler.x=-.18
for y in [-.035,.026]:
 tool=box('USB-A cutter',(-.318,y,.020),(.018,.029,.010),rubber,0);boolean_cut(body,tool);bpy.data.objects.remove(tool,do_unlink=True);box('USB-A insert',(-.314,y,.020),(.002,.024,.003),rubber,0)
# Rear port cavities are supported by the official G513QY service diagram.
for name,x,w,h in [('DC',-.245,.021,.013),('LAN',-.145,.032,.014),('HDMI',-.055,.029,.010),('USB-C',.045,.016,.007),('USB-A',.115,.029,.010)]:
 tool=box(name+' cutter',(x,.204,.019),(w,.018,h),rubber,0);boolean_cut(body,tool);bpy.data.objects.remove(tool,do_unlink=True);box(name+' shadow',(x,.198,.019),(w*.9,.002,h*.8),rubber,0)
for x in [-.22,.22]:
 for y in [-.204,.155]:box('Rubber foot',(x,y,-.002),(.06,.014,.01),rubber,.002)
blue=mat('Front light blue',(.035,.13,.5),0,.5,1.0);violet=mat('Front light violet',(.25,.025,.48),0,.5,1.0)
box('Front light left',(-.158,-.2584,.022),(.30,.002,.0016),blue,.0005);box('Front light right',(.158,-.2584,.022),(.30,.002,.0016),violet,.0005)
# Thin top and side frame, full 16:9 display, substantial lower chin, no webcam.
up=Vector((0,.2,.98)).normalized();front=Vector((0,-.98,.2)).normalized();bottom=Vector((0,.19,.06));angle=math.atan2(.2,.98)
lid=box('Thin G513 display housing',bottom+up*.204,(.642,.009,.408),black,.003);lid.rotation_euler.x=-angle
screen_mat=mat('Actual desktop display',(0,0,0));n=screen_mat.node_tree.nodes;n.clear();tex=n.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(comp/('assets/desktop/repo-screen.mp4' if (comp/'assets/desktop/repo-screen.mp4').exists() else 'assets/desktop/desktop-rx.png')));tex.image_user.frame_duration=120;tex.image_user.use_auto_refresh=True;em=n.new('ShaderNodeEmission');em.inputs['Strength'].default_value=.85;output=n.new('ShaderNodeOutputMaterial');screen_mat.node_tree.links.new(tex.outputs['Color'],em.inputs['Color']);screen_mat.node_tree.links.new(em.outputs[0],output.inputs[0])
verts=[tuple(bottom+Vector((x,0,0))+up*h+front*.005) for x,h in [(-.314,.05075),(.314,.05075),(.314,.404),(-.314,.404)]];mesh=bpy.data.meshes.new('16:9 screen');mesh.from_pydata(verts,[],[(0,1,2,3)]);o=bpy.data.objects.new('Actual KDE workspace',mesh);scene.collection.objects.link(o);mesh.materials.append(screen_mat);uv=mesh.uv_layers.new()
for loop,coord in zip(uv.data,[(0,0),(1,0),(1,1),(0,1)]):loop.uv=coord
labelmat=mat('Bezel lettering',(.09,.105,.12),.15,.5)
curve=bpy.data.curves.new('ROG STRIX lettering','FONT');curve.body='R O G   S T R I X';curve.font=bpy.data.fonts.load(str(comp/'assets/fonts/Barlow-Medium.ttf'));curve.size=.006;curve.space_character=1.1
label=bpy.data.objects.new('ROG STRIX lettering',curve);scene.collection.objects.link(label);label.location=bottom+Vector((-.225,0,0))+up*.023+front*.0052;label.rotation_euler.x=math.atan2(.98,.2);curve.materials.append(labelmat)
# The internal illustration follows ASUS service page 25; the chamber stays visible.
sys.path.insert(0,str(work))
from board_detail import build_board,build_right_blower,build_heat_spreader
internal,chip_positions=build_board(scene,work,private,mat,box)
internal+=build_right_blower(scene,mat,box)+build_heat_spreader(scene,mat,box)
for o in internal:o.hide_render=True
if mode.startswith('cut'):
 scene.eevee.taa_render_samples=32;scene.eevee.use_raytracing=False;power.hide_render=True
 # A large chassis opening retains the cooling assembly. Local apertures in the
 # heat spreader expose the chips; the bottom shell stays underneath the board.
 tool=box('Chassis illustration aperture',(-.006,.07,.08),(.416,.235,.15),black,.007);apply_modifiers(tool)
 for o in [body,deck,*keys]:
  apply_modifiers(o);boolean_cut(o,tool)
 bpy.data.objects.remove(tool,do_unlink=True)
 for o in internal:o.hide_render=False
# A neutral photographic studio keeps the actual keyboard colours in the materials.
floor=mat('Silver field',(.69,.73,.79),.02,.4);box('Studio surface',(0,0,-.012),(200,200,.01),floor,0)
def area(name,pos,power,color,size,target,size_y):
 data=bpy.data.lights.new(name,'AREA');data.energy=power;data.color=color;data.shape='RECTANGLE';data.size=size;data.size_y=size_y;o=bpy.data.objects.new(name,data);scene.collection.objects.link(o);o.location=pos;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
area('Softbox',(-.5,-.45,1.15),8,(1,.95,.9),1.1,(0,0,.15),.8);area('Edge light',(.65,.2,.95),10,(.82,.9,1),.75,(0,0,.1),.35);area('Rear light',(-.2,.75,.65),8,(.91,.94,1),.8,(0,.05,.2),.14);area('Front fill',(.1,-.75,.3),1.5,(1,.95,.9),.55,(0,0,.12),.6)
data=bpy.data.cameras.new('Camera');cam=bpy.data.objects.new('Camera',data);scene.collection.objects.link(cam);scene.camera=cam;data.lens=44

def camera_at(pos,target):cam.location=pos;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler()
if mode.startswith('cut'):data.lens=60;camera_at((.26,-.41,.61),(-.045,.075,.01))
else:camera_at((1.02,-1.25,1.48),(0,.015,.20))
if mode=='top':
 data.type='ORTHO';data.ortho_scale=.68;camera_at((0,-.026,1.5),(0,-.026,0));scene.render.resolution_x=1600;scene.render.resolution_y=1600
if mode=='intro':data.lens=65;data.dof.use_dof=True;data.dof.aperture_fstop=5.6;data.dof.focus_distance=.61
if mode in ['product','cut','intro']:
 end=87 if mode=='intro' else (105 if mode=='product' else 150);scene.frame_start=1;scene.frame_end=end
 frames=([(1,(.25,-.46,.25),(-.075,.04,.04)),(87,(.22,-.43,.24),(-.085,.05,.04))] if mode=='intro' else [(1,(1.08,-1.30,1.53),(0,.015,.20)),(105,(.96,-1.28,1.43),(0,.015,.20))] if mode=='product' else [(1,(.26,-.41,.61),(-.045,.075,.01)),(150,(.21,-.37,.56),(-.045,.075,.01))])
 for f,pos,target in frames:scene.frame_set(f);camera_at(pos,target);cam.keyframe_insert('location');cam.keyframe_insert('rotation_euler')
 for fc in cam.animation_data.action.fcurves:
  for k in fc.keyframe_points:k.interpolation='LINEAR'
 # Projection coordinates travel with the camera for the motion-design labels.
 projections=[]
 for f in [1,end]:
  scene.frame_set(f);points={}
  for name,point in list(chip_positions.items()):
   v=world_to_camera_view(scene,cam,Vector(point));points[name]=[round(v.x*1920,1),round((1-v.y)*1080,1)]
  projections.append({'frame':f,'points':points})
 (work/(mode+'-projection.json')).write_text(json.dumps(projections,indent=2));scene.frame_set(1);scene.render.filepath=str(out/(mode+'-frames')/'frame-');pathlib.Path(scene.render.filepath).parent.mkdir(parents=True,exist_ok=True);scene.frame_start=int(os.environ.get('FROST_FRAME_START','1'));scene.frame_end=int(os.environ.get('FROST_FRAME_END',str(end)))
 def cool_between_frames(_scene):
  import time
  time.sleep(float(os.environ.get('FROST_FRAME_PAUSE','0')))
 bpy.app.handlers.render_write.append(cool_between_frames)
 bpy.ops.wm.save_as_mainfile(filepath=str(private/('matched-'+mode+'.blend')))
 bpy.ops.render.render(animation=True)
else:
 scene.render.resolution_percentage=70;scene.render.filepath=str(out/(mode+'.png'));bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(private/('matched-'+mode+'.blend')))

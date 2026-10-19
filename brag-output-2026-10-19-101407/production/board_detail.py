"""G513QY cutaway geometry calibrated to ASUS service guide page 25."""
import bpy,json,math
from mathutils import Vector

def build_board(scene,work,private,mat,box):
 trace=json.loads((work/'board-trace.json').read_text());objects=[]
 def xy(px,py):return ((px-550)*.0006,.198-(py-100)*.0006)
 def comp(name,px,py,w,h,z,d,m,bevel=.0003):
  x,y=xy(px,py);o=box(name,(x,y,z),(w*.0006,h*.0006,d),m,bevel);objects.append(o);return o
 pcb=mat('Violet black solder mask',(.026,.025,.044),.15,.62)
 bs=pcb.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(.015,.024,.031,1);bs.inputs['Metallic'].default_value=.22;bs.inputs['Roughness'].default_value=.6
 noise=pcb.node_tree.nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=850;noise.inputs['Detail'].default_value=2
 bump=pcb.node_tree.nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.1;bump.inputs['Distance'].default_value=.00006;pcb.node_tree.links.new(noise.outputs['Fac'],bump.inputs['Height']);pcb.node_tree.links.new(bump.outputs['Normal'],bs.inputs['Normal'])
 pts=[xy(x,y) for x,y in trace['outline']]
 area=sum(pts[i][0]*pts[(i+1)%len(pts)][1]-pts[(i+1)%len(pts)][0]*pts[i][1] for i in range(len(pts)))
 if area<0:pts.reverse()
 count=len(pts);verts=[(x,y,z) for z in [.003,.006] for x,y in pts];faces=[tuple(range(count-1,-1,-1)),tuple(range(count,2*count))]+[(i,(i+1)%count,(i+1)%count+count,i+count) for i in range(count)]
 mesh=bpy.data.meshes.new('Traced ASUS board outline');mesh.from_pydata(verts,[],faces);mesh.update();o=bpy.data.objects.new('Service reference motherboard',mesh);scene.collection.objects.link(o);mesh.materials.append(pcb);objects.append(o)
 uv=mesh.uv_layers.new();uv.active_render=True
 for poly in mesh.polygons:
  for idx in poly.loop_indices:
   v=mesh.vertices[mesh.loops[idx].vertex_index].co;px=v.x/.0006+550;py=100+(.198-v.y)/.0006;uv.data[idx].uv=(px/trace['imageSize'][0],1-py/trace['imageSize'][1])
 substrate=mat('Chip organic substrate',(.035,.031,.028),.35,.39);gold=mat('Protective chip frame',(.22,.13,.035),.6,.36);silicon=mat('Exposed silicon',(.21,.25,.29),.87,.22);epoxy=mat('Dark moulded package',(.014,.015,.021),.22,.48);silver=mat('Tin solder',(.42,.46,.50),.85,.3);ceramic=mat('Ceramic passive bodies',(.12,.09,.06),.12,.61);black=mat('Mounting hole shadow',(.002,.003,.005),0,.8);red=mat('Package corner seal',(.22,.01,.015),.15,.42)
 # Package centres, die aspect and memory positions follow the service photograph.
 for name,px,py,w,h,die_w,die_h in [('Ryzen APU',354,323,121,84,58,43),('RX 6800M',578,350,131,132,70,70)]:
  comp(name+' substrate',px,py,w,h,.009,.006,substrate)
  # Four raised edges leave the die and its contact area visible.
  for dx,dy,bw,bh in [(0,-h/2+4,w,8),(0,h/2-4,w,8),(-w/2+4,0,8,h),(w/2-4,0,8,h)]:comp(name+' frame',px+dx,py+dy,bw,bh,.013,.0015,gold)
  die=comp(name+' exposed die',px,py,die_w,die_h,.0135,.0015,silicon,.00025)
  if name.startswith('RX'):die.rotation_euler.z=math.pi/4
  for dx in [-w/2,w/2]:
   for dy in [-h/2,h/2]:comp(name+' corner seal',px+dx,py+dy,8,8,.012,.002,red)
 for i,(x,y,w,h) in enumerate([(684,291,47,42),(684,342,47,42),(684,394,47,42),(528,467,46,42),(584,467,46,42),(639,467,46,42)]):
  comp('GDDR6 '+str(i),x,y,w,h,.0105,.006,epoxy,.0007)
  for edge in [-1,1]:comp('Memory solder edge',x+edge*(w/2),y,2,h-7,.0078,.001,silver,.0001)
 # The power stages are grouped along the rear edge of the APU and GPU.
 for i,x in enumerate([245,273,303,333,362,389,439,466,497,524,554,584,613,642,671,699]):
  comp('VRM inductor '+str(i),x,223,21,23,.011,.006,epoxy,.0012)
  comp('VRM tin top '+str(i),x,222,17,17,.0143,.0006,silver,.0003)
  comp('VRM power stage '+str(i),x,193,16,13,.0095,.005,epoxy,.0003)
 def batch(name,entries,m):
  vs=[];fs=[]
  for x,y,z,w,h,d in entries:
   j=len(vs);vs.extend([(x+a*w/2,y+b*h/2,z+c*d/2) for a,b,c in [(-1,-1,-1),(-1,-1,1),(-1,1,-1),(-1,1,1),(1,-1,-1),(1,-1,1),(1,1,-1),(1,1,1)]]);fs.extend([tuple(j+i for i in f) for f in [(0,4,6,2),(1,3,7,5),(0,1,5,4),(2,6,7,3),(0,2,3,1),(4,5,7,6)]])
  mesh=bpy.data.meshes.new(name);mesh.from_pydata(vs,[],fs);mesh.update();o=bpy.data.objects.new(name,mesh);scene.collection.objects.link(o);mesh.materials.append(m);objects.append(o)
 bodies=[];terminals=[]
 for px,py,w,h in trace['passives']:
  x,y=xy(px+w/2,py+h/2);ww=max(w*.0006,.0012);hh=max(h*.0006,.0012)
  bodies.append((x,y,.0072,ww*.7,hh*.7,.0015))
  if w>=h:
   for e in [-1,1]:terminals.append((x+e*ww*.37,y,.00715,ww*.2,hh,.0013))
  else:
   for e in [-1,1]:terminals.append((x,y+e*hh*.37,.00715,ww,hh*.2,.0013))
 batch('Service traced SMD bodies',bodies,ceramic);batch('Soldered SMD terminals',terminals,silver)
 for i,(px,py) in enumerate([(294,255),(414,256),(294,382),(414,382),(520,273),(633,273),(520,427),(633,427),(232,113),(389,120),(507,122),(712,126)]):
  x,y=xy(px,py);bpy.ops.mesh.primitive_torus_add(major_radius=.0035,minor_radius=.00065,major_segments=24,minor_segments=8,location=(x,y,.007));o=bpy.context.object;o.name='Board mounting eyelet '+str(i);o.data.materials.append(silver);objects.append(o)
  bpy.ops.mesh.primitive_cylinder_add(vertices=24,radius=.0028,depth=.0005,location=(x,y,.0067));o=bpy.context.object;o.name='Recessed mounting hole';o.data.materials.append(black);objects.append(o)
 for label,px,py in [('CPU',354,379),('GPU',578,426)]:
  c=bpy.data.curves.new('Board silkscreen','FONT');c.body=label;c.size=.004;obj=bpy.data.objects.new('Board '+label+' silkscreen',c);scene.collection.objects.link(obj);x,y=xy(px,py);obj.location=(x-.005,y,.0065);c.materials.append(silver);objects.append(obj)
 return objects,{'apu':(*xy(354,323),.017),'rx':(*xy(578,350),.017)}


def build_right_blower(scene,mat,box):
 """84-blade Arc Flow-style blower and exhaust, retained in the illustrated cutaway."""
 objects=[];cx,cy=.214,.092
 housing=mat('Blower graphite housing',(.014,.018,.024),.18,.5);blade=mat('Liquid crystal polymer fan',(.026,.030,.037),.05,.34);metal=mat('Fan hardware',(.27,.30,.34),.7,.35);dark=mat('Fin stack shadow',(.006,.009,.014),.2,.55)
 def cylinder(name,r,z,d,m,vertices=96):
  bpy.ops.mesh.primitive_cylinder_add(vertices=vertices,radius=r,depth=d,location=(cx,cy,z));o=bpy.context.object;o.name=name;o.data.materials.append(m);objects.append(o);return o
 cylinder('Fan lower housing',.067,.009,.006,housing)
 # A curved volute replaces the generic square slab. These control points
 # follow the service assembly's rounded lower shell and flattened exhaust edge.
 control=[(-.060,.061),(.037,.064),(.064,.043),(.068,-.014),(.052,-.052),(.018,-.069),(-.024,-.065),(-.056,-.041),(-.068,-.004)]
 outline=[]
 for j in range(len(control)):
  p0=Vector(control[(j-1)%len(control)]);p1=Vector(control[j]);p2=Vector(control[(j+1)%len(control)]);p3=Vector(control[(j+2)%len(control)])
  for k in range(12):
   t=k/12;v=.5*((2*p1)+(-p0+p2)*t+(2*p0-5*p1+4*p2-p3)*t*t+(-p0+3*p1-3*p2+p3)*t*t*t);outline.append((v.x,v.y))
 n=len(outline);outer=[(cx+x,cy+y) for x,y in outline];inner=[(cx+.052*math.cos(math.atan2(y,x)),cy+.052*math.sin(math.atan2(y,x))) for x,y in outline]
 verts=[(x,y,z) for z in [.011,.028] for ring in [outer,inner] for x,y in ring];faces=[]
 for j in range(n):
  k=(j+1)%n;faces.extend([(j,k,n+k,n+j),(2*n+j,3*n+j,3*n+k,2*n+k),(j,2*n+j,2*n+k,k),(n+j,n+k,3*n+k,3*n+j)])
 mesh=bpy.data.meshes.new('Contoured volute housing');mesh.from_pydata(verts,[],faces);mesh.update();cover=bpy.data.objects.new('Rounded right blower housing',mesh);scene.collection.objects.link(cover);mesh.materials.append(housing);objects.append(cover)
 bevel=cover.modifiers.new('Rolled housing edges','BEVEL');bevel.width=.0011;bevel.segments=3;cover.modifiers.new('Blower surface normals','WEIGHTED_NORMAL')
 for polygon in mesh.polygons:polygon.use_smooth=True
 bpy.ops.mesh.primitive_torus_add(major_radius=.052,minor_radius=.0009,major_segments=128,minor_segments=8,location=(cx,cy,.028));o=bpy.context.object;o.name='Rolled circular intake lip';o.data.materials.append(housing);objects.append(o)
 verts=[];faces=[]
 for i in range(84):
  phase=2*math.pi*i/84;poly=[]
  for r,twist in [(.021,0),(.032,.13),(.044,.22),(.057,.28)]:poly.append((cx+r*math.cos(phase+twist),cy+r*math.sin(phase+twist)))
  for r,twist in reversed([(.021,.040),(.032,.144),(.044,.227),(.057,.2835)]):poly.append((cx+r*math.cos(phase+twist),cy+r*math.sin(phase+twist)))
  j=len(verts);n=len(poly);verts.extend([(x,y,z) for z in [.012,.023] for x,y in poly]);faces.extend([tuple(j+k for k in range(n-1,-1,-1)),tuple(j+n+k for k in range(n))]+[(j+k,j+(k+1)%n,j+(k+1)%n+n,j+k+n) for k in range(n)])
 mesh=bpy.data.meshes.new('Curved 84 blade wheel');mesh.from_pydata(verts,[],faces);mesh.update();o=bpy.data.objects.new('Right Arc Flow blade wheel',mesh);scene.collection.objects.link(o);mesh.materials.append(blade);objects.append(o)
 cylinder('Fan motor cap',.021,.024,.005,housing)
 bpy.ops.mesh.primitive_torus_add(major_radius=.019,minor_radius=.0005,major_segments=64,minor_segments=6,location=(cx,cy,.027));o=bpy.context.object;o.name='Fan cap rim';o.data.materials.append(metal);objects.append(o)
 # Side and rear exhausts meet the enclosure's existing vents.
 for name,loc,size in [('Side blower duct',(.305,.115,.018),(.024,.095,.024)),('Rear blower duct',(.248,.176,.018),(.119,.028,.024))]:objects.append(box(name,loc,size,dark,.003))
 for i in range(48):objects.append(box('Rear heat exchanger fin',(.19+i*.0024,.187,.019),(.0006,.017,.022),metal,.0001))
 for i in range(32):objects.append(box('Side heat exchanger fin',(.315,.073+i*.0025,.018),(.012,.0006,.021),metal,.0001))
 for i,(dx,dy) in enumerate([(-.053,.057),(.056,.049),(-.046,-.051)]):
  x,y=cx+dx,cy+dy
  bpy.ops.mesh.primitive_cylinder_add(vertices=48,radius=.007,depth=.004,location=(x,y,.025));o=bpy.context.object;o.name='Formed fan mounting tab';o.data.materials.append(housing);objects.append(o)
  bpy.ops.mesh.primitive_cylinder_add(vertices=32,radius=.0032,depth=.001,location=(x,y,.0275));o=bpy.context.object;o.name='Captive fan screw';o.data.materials.append(metal);objects.append(o)
  for rot in [0,math.pi/2]:
   o=box('Fan screw drive',(x,y,.0281),(.004,.0007,.00025),dark,.0001);o.rotation_euler.z=rot;objects.append(o)
 for i,(name,color) in enumerate([('Power',(.19,.018,.012)),('Tach',(.22,.16,.015)),('PWM',(.025,.055,.14)),('Ground',(.004,.005,.007))]):
  material=mat('Fan '+name+' wire',color,0,.56);c=bpy.data.curves.new('Fan harness route','CURVE');c.dimensions='3D';c.bevel_depth=.00055;c.bevel_resolution=3;sp=c.splines.new('BEZIER');sp.bezier_points.add(3)
  for bp,p in zip(sp.bezier_points,[(.125,-.001-i*.0013,.012),(.16,-.011-i*.0013,.012),(.183,-.008-i*.0013,.013),(.203,.032-i*.0013,.012)]):bp.co=p;bp.handle_left_type='AUTO';bp.handle_right_type='AUTO'
  o=bpy.data.objects.new('Connected fan '+name+' wire',c);scene.collection.objects.link(o);c.materials.append(material);objects.append(o)
 objects.append(box('Fan cable connector',(.126,-.004,.012),(.012,.009,.005),housing,.0008))
 return objects


def build_heat_spreader(scene,mat,box):
 """Retained vapor chamber with two local illustration apertures over the dies."""
 objects=[];coat=mat('Vapor chamber graphite coating',(.017,.020,.027),.45,.47);screw=mat('Thermal retention hardware',(.25,.28,.31),.8,.35)
 profile=[(-.192,-.035),(.128,-.035),(.153,.003),(.153,.129),(.124,.159),(-.192,.159)]
 n=len(profile);verts=[(x,y,z) for z in [.020,.023] for x,y in profile];faces=[tuple(range(n-1,-1,-1)),tuple(range(n,n*2))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
 mesh=bpy.data.meshes.new('Thermal chamber outline');mesh.from_pydata(verts,[],faces);mesh.update();cover=bpy.data.objects.new('Retained vapor chamber',mesh);scene.collection.objects.link(cover);mesh.materials.append(coat);objects.append(cover)
 for name,x,y,w,h in [('APU',-.1176,.0642,.095,.075),('RX',.0168,.048,.109,.113)]:
  tool=box(name+' thermal illustration aperture',(x,y,.025),(w,h,.05),coat,.004)
  bpy.context.view_layer.objects.active=tool
  for mod in list(tool.modifiers):bpy.ops.object.modifier_apply(modifier=mod.name)
  bpy.context.view_layer.objects.active=cover;mod=cover.modifiers.new(name+' opened chip window','BOOLEAN');mod.operation='DIFFERENCE';mod.object=tool;bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(tool,do_unlink=True)
  for dx,dy in [(-w/2-.007,-h/2-.007),(-w/2-.007,h/2+.007),(w/2+.007,-h/2-.007),(w/2+.007,h/2+.007)]:
   bpy.ops.mesh.primitive_cylinder_add(vertices=32,radius=.0032,depth=.0013,location=(x+dx,y+dy,.024));o=bpy.context.object;o.name=name+' chamber retention screw';o.data.materials.append(screw);objects.append(o)
   objects.append(box('Screw head slot',(x+dx,y+dy,.0247),(.004,.0006,.0002),coat,.0001))
 bevel=cover.modifiers.new('Rolled vapor chamber edge','BEVEL');bevel.width=.001;bevel.segments=3;cover.modifiers.new('Thermal plate normals','WEIGHTED_NORMAL')
 # Broad flat condenser arms join the central chamber to the retained right blower.
 objects.append(box('Rear condenser arm',(.177,.162,.021),(.12,.022,.008),coat,.004))
 c=bpy.data.curves.new('Lower condenser return','CURVE');c.dimensions='3D';c.resolution_u=24;c.bevel_depth=.006;c.bevel_resolution=5;c.use_fill_caps=True;sp=c.splines.new('BEZIER');sp.bezier_points.add(4)
 for bp,p in zip(sp.bezier_points,[(.126,-.023,0),(.22,-.023,0),(.29,-.007,0),(.312,.035,0),(.312,.103,0)]):bp.co=p;bp.handle_left_type='AUTO';bp.handle_right_type='AUTO'
 o=bpy.data.objects.new('Flattened condenser return to side fins',c);scene.collection.objects.link(o);o.location.z=.019;o.scale.z=.26;c.materials.append(coat);objects.append(o)
 return objects

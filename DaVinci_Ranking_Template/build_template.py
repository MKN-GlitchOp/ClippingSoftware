from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import json,zipfile,re
p=Path('H:/Clipping/DaVinci_Ranking_Template')
nodes={};exposed=[]
def inp(v=None,expression=None,source=None):
 if expression is not None:return 'Input { Expression = '+json.dumps(expression)+', }'
 if source:return 'Input { SourceOp = '+json.dumps(source)+', Source = "Output", }'
 if isinstance(v,str):v=json.dumps(v)
 elif isinstance(v,list):v='{ '+', '.join(map(str,v))+' }'
 return 'Input { Value = '+str(v)+', }'
def node(name,typ,inputs,user=None):
 body='\n'.join(f'                    {k} = {v},' for k,v in inputs.items())
 extra='' if user is None else '\n                UserControls = ordered() {\n'+user+'\n                },'
 nodes[name]=f'''            {name} = {typ} {{
                NameSet = true,
                Inputs = {{
{body}
                }},
                ViewInfo = OperatorInfo {{ Pos = {{ {len(nodes)*110}, 0 }} }},{extra}
            }},'''
def expose(op,source,name):
 exposed.append(f'            Control{len(exposed)+1} = InstanceInput {{ SourceOp = "{op}", Source = "{source}", Name = {json.dumps(name)}, Page = "Controls", }},')
controls=[('ActiveRank','Active rank (5 to 1)',5,1,5,True),('RevealEarlier','Keep earlier labels visible',1,0,1,True),('BlackPanels','Black panels',1,0,1,True),('TitleSize','Heading size',75/1080,.025,.12,False),('LabelSize','Label size',58/1080,.02,.10,False),('NumberSize','Number size',64/1080,.02,.10,False)]
ucs=[]
base={'Width':inp(1080),'Height':inp(1920),'UseFrameFormatSettings':inp(1),'TopLeftAlpha':inp(0)}
for key,label,default,mini,maxi,integer in controls:
 base[key]=inp(default)
 ctrl='CheckboxControl' if key in ['RevealEarlier','BlackPanels'] else 'SliderControl'
 ucs.append(f'                    {key} = {{ LINKS_Name = {json.dumps(label)}, LINKID_DataType = "Number", INPID_InputControl = "{ctrl}", INP_Default = {default}, INP_MinScale = {mini}, INP_MaxScale = {maxi}, INP_MinAllowed = {mini}, INP_MaxAllowed = {maxi}, INP_Integer = {str(integer).lower()}, IC_ControlPage = 0, }},')
node('Controls','Background',base,'\n'.join(ucs))
for key,label,*_ in controls:expose('Controls',key,label)
prev='Controls'
def merge(fg):
 global prev
 name='Merge'+str(len(nodes));node(name,'Merge',{'Background':inp(source=prev),'Foreground':inp(source=fg),'PerformDepthMerge':inp(0)});prev=name
for name,top,bottom in [('Top',0,535),('Bottom',1143,1920)]:
 node(name+'Mask','RectangleMask',{'Center':inp([.5,1-(top+bottom)/2/1920]),'Width':inp(1),'Height':inp((bottom-top)/1920),'Solid':inp(1)})
 node(name+'Panel','Background',{'Width':inp(1080),'Height':inp(1920),'UseFrameFormatSettings':inp(1),'TopLeftAlpha':inp(expression='Controls.BlackPanels'),'EffectMask':inp(source=name+'Mask')})
 merge(name+'Panel')
def txt(name,text,x,y,size,color=(1,1,1),left=True,opacity=None):
 inputs={'Width':inp(1080),'Height':inp(1920),'UseFrameFormatSettings':inp(1),'StyledText':inp(text),'Font':inp('Arial'),'Style':inp('Bold'),'Size':inp(expression=size),'Center':inp([x/1080,1-y/1920]),'HorizontalLeftCenterRight':inp(-1 if left else 0),'HorizontalJustificationNew':inp(3),'VerticalTopCenterBottom':inp(0),'VerticalJustificationNew':inp(3)}
 for key,val in zip(['Red1','Green1','Blue1'],color):inputs[key]=inp(expression=val) if isinstance(val,str) else inp(val)
 if opacity:inputs['Opacity1']=inp(expression=opacity)
 node(name,'TextPlus',inputs);merge(name)
# Title fragments retain the precise positions of the approved two-colour heading.
f=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',75)
for row,y,parts in [(1,310,[('Ranking ',(1,1,1)),('Funniest',(1,231/255,55/255))]),(2,400,[('Streamer ',(1,1,1)),('Moments',(86/255,233/255,1))])]:
 widths=[f.getlength(t) for t,c in parts];x=(1080-sum(widths))/2
 for part,((t,c),width) in enumerate(zip(parts,widths),1):
  name=f'Heading{row}_{part}';txt(name,t,x,y,'Controls.TitleSize',c);expose(name,'StyledText',f'Heading {row} - '+('white text' if part==1 else 'highlighted text'));expose(name,'Center',f'Heading {row} - part {part} position');x+=width
labels={1:'Wrong door',2:'Fake tough guy',3:'Chat roasts',4:'Jackie Chan',5:'Room tour'}
for rank in range(1,6):
 active=f'Controls.ActiveRank == {rank}'
 cy=1225+(rank-1)*80
 txt(f'Rank{rank}',f'{rank}.',65,cy,'Controls.NumberSize',(1,f'iif({active},231/255,1)',f'iif({active},55/255,1)'))
 visible=f'iif(Controls.RevealEarlier > 0.5, iif({rank} >= Controls.ActiveRank,1,0), iif({active},1,0))'
 txt(f'Label{rank}',labels[rank],165,cy,'Controls.LabelSize',(f'iif({active},86/255,0.8)',f'iif({active},233/255,0.8)',f'iif({active},1,0.8)'),opacity=visible)
 expose(f'Label{rank}','StyledText',f'Rank {rank} label')
text='''{
    Tools = ordered() {
        RankingShorts = MacroOperator {
            NameSet = true,
            Inputs = ordered() {
'''+ '\n'.join(exposed)+'''
            },
            Outputs = {
                MainOutput1 = InstanceOutput { SourceOp = "'''+prev+'''", Source = "Output", },
            },
            ViewInfo = GroupInfo { Pos = { 0, 0 } },
            Tools = ordered() {
'''+ '\n'.join(nodes.values())+'''
            },
        },
    },
    ActiveTool = "RankingShorts",
}
'''
setting=p/'Ranking Shorts.setting';setting.write_text(text,encoding='utf-8')
# Validate node wiring and macro destinations, not just archive integrity.
refs=re.findall(r'SourceOp = "([^"]+)"',text)
assert all(r in nodes for r in refs),set(refs)-set(nodes)
assert text.count(' = TextPlus {')==14
# Lexically check all paired brackets outside strings.
stack=[];quoted=False;escaped=False
for char in text:
 if quoted:
  if escaped:escaped=False
  elif char=='\\':escaped=True
  elif char=='"':quoted=False
 else:
  if char=='"':quoted=True
  elif char in '{[(':stack.append(char)
  elif char in '}])':assert stack.pop()==dict(zip('}])','{[('))[char]
assert not stack and not quoted
with zipfile.ZipFile(p/'Ranking Shorts.drfx','w',zipfile.ZIP_DEFLATED) as z:
 z.write(setting,'Edit/Titles/Clipping/Ranking Shorts.setting')
 preview=Image.open('H:/Clipping/top5_final/preview_1.jpg');preview.thumbnail((320,180))
 thumb=Image.new('RGB',(320,180),'black');thumb.paste(preview,((320-preview.width)//2,0));thumb.save(p/'Ranking Shorts.wide.png')
 z.write(p/'Ranking Shorts.wide.png','Edit/Titles/Clipping/Ranking Shorts.wide.png')
with zipfile.ZipFile(p/'Ranking Shorts.drfx') as z:assert z.testzip() is None
readme='''Ranking Shorts — editable Text+ Fusion Title

INSTALL
1. Double-click Ranking Shorts.drfx and accept Resolve's template installation.
2. Reopen Resolve if needed. Find Ranking Shorts in Effects > Titles > Clipping.
3. Set your timeline to 1080 x 1920 before adding the title.

USE
Place your source footage on V1 and the title on V2.
The transparent video window is full width, 608 pixels high, starting 535 pixels below the top. For a 1920 x 1080 source, use Scale entire image to fit; move the video up about 121 pixels from the frame centre (Transform Position Y about +121). The window centre is at pixel (540, 839).
Split or duplicate the title at each clip boundary. Set Active rank to 5, 4, 3, 2, then 1. Change the five Rank label fields in the Inspector. Copy titles so their label text stays consistent.
Keep earlier labels visible fills the list progressively; turn it off to show only the current label. Empty any label field you do not need.
The heading has four editable text fragments, matching the white/yellow and white/cyan design. Keep the first white fragment's trailing space. If you change word lengths substantially, adjust the exposed heading positions to keep the two parts neatly aligned.
Heading, label and number sizes are editable. Black panels can be turned off for a transparent text-only overlay. Labels share row centres with their numbers, and finish above the lower app controls.
No captions, music, sound effects, fonts or footage are included. Uses standard Arial Bold and built-in Fusion nodes; no Studio-only effects.

MANUAL INSTALL FALLBACK
Copy Ranking Shorts.setting into:
%APPDATA%\\Blackmagic Design\\DaVinci Resolve\\Support\\Fusion\\Templates\\Edit\\Titles\\Clipping\\
Create the Clipping folder if needed, then restart Resolve.

VALIDATION
The package archive, all macro control targets, node connections and bracket structure have been checked against the format of Resolve's installed title templates. It has not been opened or rendered inside Resolve, so the first in-app render remains unverified.
'''
(p/'Read Me.txt').write_text(readme,encoding='utf-8')
(p/'validation.txt').write_text(f'PASS: archive integrity; {len(nodes)} nodes; {len(exposed)} Inspector controls; {len(refs)} valid node references; balanced syntax; 14 TextPlus nodes.\nResolve runtime render: not performed.\n',encoding='utf-8')
print(str(p/'Ranking Shorts.drfx'))
print(f'{len(nodes)} nodes, {len(exposed)} controls; validation passed')

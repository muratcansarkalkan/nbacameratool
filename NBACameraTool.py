import os, re, math, struct, shutil, tkinter as tk
from tkinter import ttk, filedialog, messagebox

APP_TITLE = 'NBA Live MGD Camera Editor v0.3.5-alpha'
NUMERIC_SIZES = {4, 8, 12, 16}

# Human-readable research notes for known camera-controller fields.
# Wording is intentionally conservative where runtime behavior is not fully decoded.
def describe_camera_value(name):
    n=name.lower()
    exact={
        'position': ('Camera position', 'Base camera location in NBA Live world coordinates (X, Y, Z).'),
        'maxzoomdiff': ('Maximum dynamic zoom', 'Caps how much situational zoom may differ from the base framing.'),
        'aimtargetzratio': ('Aim target height influence', 'How strongly target Z/height contributes to the point the camera aims at.'),
        'netx': ('Basket X reference', 'Court/basket X reference used by the camera controller.'),
        'controllerpriority': ('Controller priority', 'Likely priority/order for this camera controller. Avoid changing unless testing controller selection.'),
        'timerfreq': ('Controller update frequency', 'Likely timing/update parameter for the camera controller. Experimental.'),
    }
    if n in exact: return exact[n]
    if n.startswith('zoom_min_'):
        return ('Base zoom minimum', 'Lower endpoint of a base framing/zoom state. Smaller values produced tighter framing in our long-distance Press Box tests.')
    if n.startswith('zoom_max_'):
        return ('Base zoom maximum', 'Upper endpoint of a base framing/zoom state. Together with zoom_min_* it defines the available base framing range.')
    if n.startswith('zoomdiff_dunk_'):
        return ('Dunk zoom change', 'Situational zoom offset used around dunk/rim-action behavior. Increase cautiously to add a small push-in.')
    if n.startswith('zoomdiff_target'):
        return ('Target zoom change', 'Zoom offset driven by the current tracked gameplay target. Likely active during ordinary play.')
    if n.startswith('zoomdiff_jumpba'):
        return ('Jump-ball zoom change', 'Situational zoom offset used for jump-ball behavior.')
    if n.startswith('zoomdiff_playca'):
        return ('Play-call zoom change', 'Situational zoom offset associated with play-call behavior.')
    if n.startswith('zoomdiff_oneono'):
        return ('One-on-one zoom change', 'Situational zoom offset associated with one-on-one gameplay behavior.')
    if n.startswith('pitch_zoomdiff_'):
        return ('Pitch-based zoom change', 'Links vertical camera angle/pitch to zoom. Useful for dynamic framing; excessive values can cause pumping.')
    if n.startswith('maxaimoffset_'):
        return ('Maximum aim offset', 'Limits how far the camera aim point can move away from its normal target. Lower = more static composition.')
    if n.startswith('scaletargety_'):
        return ('Vertical target tracking', 'Scales how strongly target Y/vertical movement influences camera aiming. Lower = steadier framing.')
    if n.startswith('hmin_'):
        return ('Minimum heading', 'Lower horizontal-rotation/heading limit. Works with hmax_* to define how far the camera may swivel.')
    if n.startswith('hmax_'):
        return ('Maximum heading', 'Upper horizontal-rotation/heading limit. Narrower hmin/hmax span = more static horizontal camera.')
    if n.startswith('orientationvisc'):
        return ('Orientation viscosity', 'Rotation damping/resistance. Higher generally makes panning smoother and less immediate.')
    if n.startswith('orientationcoup'):
        return ('Orientation coupling', 'How strongly camera orientation follows its target/controller. Lower generally loosens target following.')
    if n.startswith('orientationmaxv'):
        return ('Maximum angular velocity', 'Maximum rotation speed. Lower values reduce whip-pans and make the camera feel more static.')
    if n.startswith('orientationtole'):
        return ('Orientation tolerance', 'Likely rotational tolerance/dead-zone before correction. Exact runtime interpretation remains experimental.')
    if n.startswith('zoom_netdist_min'):
        return ('Net-distance minimum', 'Lower gameplay-distance threshold for zoom behavior relative to the basket/net. Experimental; not camera-to-court distance.')
    if n.startswith('zoom_netdist_max'):
        return ('Net-distance maximum', 'Upper gameplay-distance threshold for zoom behavior relative to the basket/net. Experimental; not camera-to-court distance.')
    if n.startswith('dunkdelaytime_'):
        return ('Dunk zoom delay', 'Likely delay/timing value for dunk-related camera behavior. Experimental.')
    if n.startswith('zoomcontroller'):
        return ('Zoom controller', 'Controller reference/parameter rather than a direct visual setting. Avoid arbitrary edits.')
    return (name, 'Undocumented numeric controller value. Edit only with a backup and compare one change at a time.')


def camera_value_status(name):
    """Research confidence for camera fields based on file structure + in-game tests."""
    n=name.lower()
    confirmed=(
        n=='position' or n.startswith('zoom_min_') or n.startswith('zoom_max_') or
        n.startswith('scaletargety_') or n.startswith('hmin_') or n.startswith('hmax_') or
        n.startswith('orientationmaxv')
    )
    likely=(
        n=='maxzoomdiff' or n.startswith('zoomdiff_') or n.startswith('pitch_zoomdiff_') or
        n.startswith('maxaimoffset_') or n=='aimtargetzratio' or
        n.startswith('orientationvisc') or n.startswith('orientationcoup')
    )
    if confirmed: return 'Confirmed'
    if likely: return 'Likely'
    return 'Experimental'

PRESSBOX_GUIDE = '''PRESS BOX CAMERA PARAMETER GUIDE

WORKFLOW
1. Set the arena-specific Press Box XYZ position.
2. Choose Live Broadcast.
3. Click Apply Broadcast Build.
4. Save the MGD and test in-game.
5. Change only one family at a time when fine-tuning.

CURRENT LIVE BROADCAST BASELINE
Dynamic zoom / push-in:       12%
Aim freedom:                  25%
Vertical target following:    45%
Horizontal rotation range:    50%
Target-height influence:      30%
Base framing range:           25%
Distance compensation:       100% (Inverse)
Pan damping / viscosity:     130%
Target-follow coupling:       85%
Maximum pan speed:            55%
Pan correction tolerance:     80%

ARENA EXAMPLE
Memphis Press Box test position: X=-3, Y=-125, Z=45.
This is an arena-specific mount position, not a universal NBA Live 2005 position.

CONFIRMED / STRONGLY TESTED
position
  Physical camera location (X, Y, Z).

zoom_min_* / zoom_max_*
  Base framing range. In long-distance Press Box tests, smaller values tightened the view.
  Inverse distance compensation has worked when moving the physical camera farther away.

scaletargety_*
  Position-aware vertical pitch/following. Increasing this made the camera correct its
  vertical framing better as play moved to a different depth/side of the court.

hmin_* / hmax_*
  Horizontal heading/swivel envelope. Narrower range = a more static camera.

orientationmaxv*
  Maximum pan/angular speed. Lower values reduce whip-pans.

LIKELY
maxaimoffset_*
  Aim freedom/clamp. Lower values keep composition more anchored.

aimtargetzratio
  Target-height influence. Best candidate for making the camera pitch upward more when
  a shot, lob, or other tracked target rises vertically.

orientationvisc*
  Pan damping/resistance. Higher generally feels heavier/smoother.

orientationcoup*
  How strongly orientation follows the calculated target.

maxzoomdiff / zoomdiff_* / pitch_zoomdiff_*
  Dynamic/situational zoom family. Controls gameplay-driven push-ins and zoom variation.

EXPERIMENTAL
zoom_netdist_min/max
  Appears to define a gameplay-distance window relative to the basket/net. Keep separate
  from physical camera distance until the runtime math is better understood.

orientationtole*
  Likely correction tolerance/dead-zone. Exact interpretation is not yet established.

dunkdelaytime_*
  Likely timing/delay for dunk-related camera behavior.

TUNING NOTES
- Player/action too high or low as play changes court depth: adjust Vertical target following
  (scaletargety_*).
- Camera does not look upward enough on shots/lobs: test Target-height influence
  (aimtargetzratio), then maxaimoffset_* if it appears clamped.
- Too much left/right rotation: reduce Horizontal rotation range (hmin/hmax envelope).
- Camera whips too quickly: reduce Maximum pan speed (orientationmaxv*).
- Camera feels twitchy: increase Pan damping / viscosity gradually.
- Too much zoom pumping: reduce Dynamic zoom / push-in.
- Farther physical camera looks too wide: use Inverse distance compensation for base framing.

Research labels describe the current state of reverse engineering and can change as more
in-game tests establish the exact controller math.'''


class Record:
    def __init__(self, offset, size, name, values, block='Global'):
        self.offset=offset; self.size=size; self.name=name; self.values=list(values); self.block=block
    @property
    def value_offset(self): return self.offset + 20

class MGD:
    def __init__(self, path):
        self.path=path; self.data=bytearray(open(path,'rb').read())
        if b'UBIBIN' not in self.data[:64] or b'NBACAM' not in self.data[:128]:
            raise ValueError('Not a recognized NBACAM/UBIBIN MGD file.')
        self.camera_starts=self._camera_starts()
        self.records=self._records()
    def _ascii_strings(self):
        return [(m.start(),m.group().decode('ascii','ignore')) for m in re.finditer(rb'[\x20-\x7e]{4,}',self.data)]
    def _camera_starts(self):
        hits=[]
        for off,s in self._ascii_strings():
            if s.startswith('Camera_') or s.startswith('AmbientCamera_'):
                hits.append((off,s))
        # first occurrences form the directory; actual blocks occur later. Keep occurrences >= 0x200.
        actual=[x for x in hits if x[0] >= 0x200]
        # directory can extend beyond 0x200 in later files; actual block names have a large gap from directory.
        if actual:
            gaps=[actual[i+1][0]-actual[i][0] for i in range(len(actual)-1)]
            # Find first occurrence followed by normal multi-KB block spacing, or simply first >= 0x280.
            # Known files place first real block around 0x2D0-0x418.
            actual=[x for x in hits if x[0] >= 0x2C0]
        # De-duplicate only exact offset; duplicate camera names are legitimate.
        return actual
    def _block_for(self, off):
        starts=[x for x in self.camera_starts if x[0] <= off]
        if not starts: return 'Global / Setup'
        idx=len(starts)-1; name=starts[-1][1]
        same=sum(1 for o,n in self.camera_starts[:idx+1] if n==name)
        total=sum(1 for o,n in self.camera_starts if n==name)
        return f'{name} #{same}' if total>1 else name
    def _records(self):
        out=[]; b=self.data
        for off in range(0,len(b)-28,4):
            size=struct.unpack_from('<I',b,off)[0]
            if size not in NUMERIC_SIZES: continue
            nameb=bytes(b[off+4:off+20])
            if b'\0' not in nameb: continue
            rawname=nameb.split(b'\0',1)[0]
            if len(rawname)<2 or any(c < 32 or c >= 127 for c in rawname): continue
            name=rawname.decode('ascii')
            end=off+20+2*size
            if end>len(b): continue
            le=bytes(b[off+20:off+20+size]); mirror=bytes(b[off+20+size:end])
            if not all(mirror[i:i+4]==le[i:i+4][::-1] for i in range(0,size,4)): continue
            vals=struct.unpack('<'+'f'*(size//4),le)
            # Suppress obvious serialized IDs/pointers interpreted as denormal floats.
            if size==4 and vals[0] != 0.0 and abs(vals[0]) < 1e-20: continue
            if not all(math.isfinite(v) for v in vals): continue
            out.append(Record(off,size,name,vals,self._block_for(off)))
        return out
    def write_record(self, rec, values):
        if len(values)*4 != rec.size: raise ValueError('Wrong component count')
        le=struct.pack('<'+'f'*len(values),*values)
        mirror=b''.join(le[i:i+4][::-1] for i in range(0,len(le),4))
        p=rec.value_offset; self.data[p:p+rec.size]=le; self.data[p+rec.size:p+2*rec.size]=mirror
        rec.values=list(values)
    def save(self,path):
        with open(path,'wb') as f: f.write(self.data)

class App:
    def __init__(self,root):
        self.root=root; root.title(APP_TITLE); root.geometry('980x650')
        self.mgd=None; self.path=None; self.vars=[]
        self._menu(); self._ui()
    def _menu(self):
        m=tk.Menu(self.root); fm=tk.Menu(m,tearoff=0)
        fm.add_command(label='Open MGD...',command=self.open)
        fm.add_command(label='Save',command=self.save)
        fm.add_command(label='Save As...',command=self.save_as)
        fm.add_separator(); fm.add_command(label='Export Selected Camera to Blender...',command=self.export_blender_selected)
        fm.add_command(label='Export All Recognized Presets...',command=self.export_blender_all)
        fm.add_separator(); fm.add_command(label='Exit',command=self.root.destroy)
        m.add_cascade(label='File',menu=fm)
        tm=tk.Menu(m,tearoff=0)
        tm.add_command(label='Press Box Designer...',command=self.pressbox_designer)
        m.add_cascade(label='Tools',menu=tm)
        hm=tk.Menu(m,tearoff=0)
        hm.add_command(label='Camera Parameter Guide...',command=self.show_parameter_guide)
        m.add_cascade(label='Help',menu=hm)
        self.root.config(menu=m)
    def show_parameter_guide(self):
        win=tk.Toplevel(self.root); win.title('Camera Parameter Guide'); win.geometry('860x680'); win.transient(self.root)
        outer=ttk.Frame(win,padding=10); outer.pack(fill='both',expand=True)
        ttk.Label(outer,text='Press Box Camera Parameter Guide',font=('',11,'bold')).pack(anchor='w',pady=(0,6))
        ttk.Label(outer,text='Confirmed = supported by direct in-game tests; Likely = strong structural/behavioral evidence; Experimental = not fully decoded.',wraplength=820).pack(anchor='w',pady=(0,8))
        frame=ttk.Frame(outer); frame.pack(fill='both',expand=True)
        text=tk.Text(frame,wrap='word',undo=False,font=('TkFixedFont',10))
        sb=ttk.Scrollbar(frame,orient='vertical',command=text.yview); text.configure(yscrollcommand=sb.set)
        text.pack(side='left',fill='both',expand=True); sb.pack(side='right',fill='y')
        text.insert('1.0',PRESSBOX_GUIDE); text.configure(state='disabled')
        ttk.Button(outer,text='Close',command=win.destroy).pack(anchor='e',pady=(8,0))

    def _ui(self):
        top=ttk.Frame(self.root,padding=8); top.pack(fill='x')
        self.info=ttk.Label(top,text='Open an NBA Live nbacam.mgd file.'); self.info.pack(side='left')
        ttk.Label(top,text='Filter:').pack(side='right',padx=(8,3))
        self.filter=tk.StringVar(); e=ttk.Entry(top,textvariable=self.filter,width=24); e.pack(side='right'); e.bind('<KeyRelease>',lambda _:self.refresh())
        self.nb=ttk.Notebook(self.root); self.nb.pack(fill='both',expand=True,padx=8,pady=(0,8))
    def open(self):
        p=filedialog.askopenfilename(filetypes=[('NBA Camera MGD','*.mgd'),('All files','*.*')])
        if not p:return
        try:
            new_mgd=MGD(p)
        except Exception as e:
            messagebox.showerror('Open failed',str(e)); return
        # Do not let editor variables from a previously opened file commit into the new MGD.
        self.vars=[]
        self.mgd=new_mgd; self.path=p
        self.info.config(text=f'{os.path.basename(p)} — {len(self.mgd.records)} editable numeric records, {len(self.mgd.camera_starts)} camera blocks')
        self.refresh(commit_pending=False)
    def commit(self):
        if not self.mgd:return True
        try:
            for rec,vs in self.vars:
                vals=[float(v.get()) for v in vs]; self.mgd.write_record(rec,vals)
            return True
        except Exception as e: messagebox.showerror('Invalid value',str(e)); return False
    def refresh(self, commit_pending=True, target_block=None):
        if not self.mgd:return
        # Remember the currently visible camera tab. Rebuilding a ttk.Notebook otherwise
        # always selects its first tab (usually AmbientCamera_F), which made successful
        # programmatic edits look as if they had been reverted.
        selected_text=None
        try:
            current=self.nb.select()
            if current:
                selected_text=self.nb.tab(current,'text')
        except tk.TclError:
            pass
        if target_block is not None:
            selected_text=target_block

        # Normal refreshes preserve edits. Programmatic record writes can explicitly
        # skip this commit so stale Entry values do not overwrite the new values.
        if commit_pending and self.vars and not self.commit(): return
        for t in self.nb.tabs(): self.nb.forget(t)
        self.vars=[]; q=self.filter.get().lower().strip()
        groups={}
        for r in self.mgd.records:
            if q and q not in r.name.lower() and q not in r.block.lower(): continue
            groups.setdefault(r.block,[]).append(r)
        for block,recs in groups.items():
            frame=ttk.Frame(self.nb); self.nb.add(frame,text=block)
            canvas=tk.Canvas(frame,highlightthickness=0); sb=ttk.Scrollbar(frame,orient='vertical',command=canvas.yview)
            inner=ttk.Frame(canvas); inner.bind('<Configure>',lambda e,c=canvas:c.configure(scrollregion=c.bbox('all')))
            canvas.create_window((0,0),window=inner,anchor='nw'); canvas.configure(yscrollcommand=sb.set)
            canvas.pack(side='left',fill='both',expand=True); sb.pack(side='right',fill='y')
            for row,r in enumerate(recs):
                ttk.Label(inner,text=r.name,width=24).grid(row=row,column=0,sticky='w',padx=6,pady=3)
                vs=[]
                labels='XYZW' if len(r.values)>1 else ''
                for j,v in enumerate(r.values):
                    if labels: ttk.Label(inner,text=labels[j]).grid(row=row,column=1+j*2,sticky='e')
                    sv=tk.StringVar(value=f'{v:.9g}'); vs.append(sv)
                    ttk.Entry(inner,textvariable=sv,width=14).grid(row=row,column=2+j*2,padx=(2,8),pady=3)
                ttk.Label(inner,text=f'0x{r.value_offset:X}',foreground='#777').grid(row=row,column=10,sticky='w',padx=8)
                friendly,desc=describe_camera_value(r.name)
                status=camera_value_status(r.name)
                ttk.Label(inner,text=f'[{status}] {friendly}: {desc}',foreground='#666',wraplength=390,justify='left').grid(row=row,column=11,sticky='w',padx=(4,10),pady=3)
                self.vars.append((r,vs))

        # Restore/select the requested camera after rebuilding all tabs.
        if selected_text:
            for tab_id in self.nb.tabs():
                if self.nb.tab(tab_id,'text') == selected_text:
                    self.nb.select(tab_id)
                    break
    def save(self):
        if not self.path or not self.mgd:return
        if not self.commit():return
        bak=self.path+'.bak'
        if not os.path.exists(bak): shutil.copyfile(self.path,bak)
        self.mgd.save(self.path); messagebox.showinfo('Saved',f'Saved MGD.\nBackup: {bak}\n\nBoth little-endian values and the mirrored byte-order copies were updated.')
    def save_as(self):
        if not self.mgd:return
        if not self.commit():return
        p=filedialog.asksaveasfilename(defaultextension='.mgd',filetypes=[('NBA Camera MGD','*.mgd')])
        if p:self.mgd.save(p);self.path=p;messagebox.showinfo('Saved',f'Saved {p}')

    def _records_for_block(self, block):
        return [r for r in self.mgd.records if r.block == block]

    @staticmethod
    def _find_record(records, name, occurrence=0, size=None):
        matches=[r for r in records if r.name.lower()==name.lower() and (size is None or r.size==size)]
        return matches[occurrence] if occurrence < len(matches) else None

    def _pressbox_block(self):
        if not self.mgd: return None
        blocks=[]
        for r in self.mgd.records:
            if 'PRESSBOX' in r.block.upper() and r.block not in blocks:
                blocks.append(r.block)
        if not blocks:
            return None
        if len(blocks)==1:
            return blocks[0]
        # Use existing chooser semantics but restrict to Press Box blocks.
        win=tk.Toplevel(self.root); win.title('Choose Press Box'); win.transient(self.root); win.grab_set(); win.resizable(False,False)
        body=ttk.Frame(win,padding=12); body.pack(fill='both',expand=True)
        ttk.Label(body,text='Press Box block:').grid(row=0,column=0,columnspan=2,sticky='w',pady=(0,6))
        choice=tk.StringVar(value=blocks[0])
        ttk.Combobox(body,textvariable=choice,values=blocks,state='readonly',width=34).grid(row=1,column=0,columnspan=2,sticky='ew')
        result={'value':None}
        def ok(): result['value']=choice.get(); win.destroy()
        ttk.Button(body,text='OK',command=ok).grid(row=2,column=0,pady=(10,0),padx=(0,4))
        ttk.Button(body,text='Cancel',command=win.destroy).grid(row=2,column=1,pady=(10,0),padx=(4,0))
        win.bind('<Return>',lambda e:ok()); win.bind('<Escape>',lambda e:win.destroy())
        self.root.wait_window(win)
        return result['value']

    def pressbox_designer(self):
        if not self.mgd:
            messagebox.showinfo('Press Box Designer','Open an MGD first.')
            return
        if not self.commit(): return
        block=self._pressbox_block()
        if not block:
            messagebox.showwarning('Press Box Designer','No Camera_PRESSBOX block was found in this MGD.')
            return
        recs=self._records_for_block(block)
        pos=self._find_record(recs,'position',size=12)
        if not pos:
            messagebox.showwarning('Press Box Designer',f'{block} has no 3-float position record.')
            return
        netx=self._find_record(recs,'netx',size=4)
        netxv=netx.values[0] if netx else 40.0

        win=tk.Toplevel(self.root); win.title(f'Press Box Designer — {block}'); win.transient(self.root); win.grab_set()
        # The designer has grown into a full calibration panel. Keep it usable on
        # 768p displays by making the whole dialog vertically scrollable.
        win.geometry('1180x700')
        shell=ttk.Frame(win); shell.pack(fill='both',expand=True)
        page=tk.Canvas(shell,highlightthickness=0)
        page_scroll=ttk.Scrollbar(shell,orient='vertical',command=page.yview)
        body=ttk.Frame(page,padding=12)
        body_window=page.create_window((0,0),window=body,anchor='nw')
        body.bind('<Configure>',lambda e:page.configure(scrollregion=page.bbox('all')))
        page.bind('<Configure>',lambda e:page.itemconfigure(body_window,width=e.width))
        page.configure(yscrollcommand=page_scroll.set)
        page.pack(side='left',fill='both',expand=True); page_scroll.pack(side='right',fill='y')
        def _wheel(e):
            page.yview_scroll(int(-1*(e.delta/120)), 'units')
        page.bind_all('<MouseWheel>',_wheel)
        win.bind('<Destroy>',lambda e: page.unbind_all('<MouseWheel>') if e.widget is win else None)
        body.columnconfigure(1,weight=1); body.columnconfigure(2,weight=1); body.columnconfigure(3,weight=1)
        ttk.Label(body,text='Coupled Press Box profile',font=('',10,'bold')).grid(row=0,column=0,columnspan=4,sticky='w')
        ttk.Label(body,text='Build a Press Box camera in layers: physical position, base framing, gameplay motion, then pan response. Labels below describe the best current interpretation of each MGD field; items marked Experimental are not fully decoded yet.',wraplength=1120).grid(row=1,column=0,columnspan=4,sticky='w',pady=(3,10))

        ttk.Label(body,text='').grid(row=2,column=0)
        for j,h in enumerate(('X','Y','Z'),1): ttk.Label(body,text=h).grid(row=2,column=j)
        ttk.Label(body,text='Current MGD').grid(row=3,column=0,sticky='w')
        current_vars=[tk.StringVar(value=f'{v:.4f}') for v in pos.values]
        for j,sv in enumerate(current_vars,1): ttk.Label(body,textvariable=sv).grid(row=3,column=j,padx=5)
        ttk.Label(body,text='Proposed').grid(row=4,column=0,sticky='w')
        pv=[tk.StringVar(value=f'{v:.4f}') for v in pos.values]
        for j,sv in enumerate(pv,1): ttk.Entry(body,textvariable=sv,width=12).grid(row=4,column=j,padx=5,pady=2)

        ttk.Label(body,text='Aim target').grid(row=5,column=0,sticky='w',pady=(8,0))
        tv=[tk.StringVar(value='0.0'),tk.StringVar(value='0.0'),tk.StringVar(value='5.0')]
        for j,sv in enumerate(tv,1): ttk.Entry(body,textvariable=sv,width=12).grid(row=5,column=j,padx=5,pady=(8,2))
        ttk.Label(body,text=f'Basket X reference (netx): {netxv:.3f}').grid(row=6,column=0,columnspan=4,sticky='w',pady=(4,8))

        metrics=tk.StringVar(value='')
        ttk.Label(body,textvariable=metrics,justify='left').grid(row=7,column=0,columnspan=4,sticky='w',pady=(4,10))

        # Expose the whole numeric Press Box controller here, not just XYZ. This lets
        # position, zoom limits, aim limits, damping and situational zoom offsets be
        # tuned as one profile while we continue decoding their exact runtime math.
        ctl_box=ttk.LabelFrame(body,text='Press Box controller values',padding=8)
        ctl_box.grid(row=8,column=0,columnspan=4,sticky='nsew',pady=(2,10))
        ctl_canvas=tk.Canvas(ctl_box,height=235,highlightthickness=0)
        ctl_scroll=ttk.Scrollbar(ctl_box,orient='vertical',command=ctl_canvas.yview)
        ctl_inner=ttk.Frame(ctl_canvas)
        ctl_inner.bind('<Configure>',lambda e:ctl_canvas.configure(scrollregion=ctl_canvas.bbox('all')))
        ctl_canvas.create_window((0,0),window=ctl_inner,anchor='nw')
        ctl_canvas.configure(yscrollcommand=ctl_scroll.set)
        ctl_canvas.pack(side='left',fill='both',expand=True); ctl_scroll.pack(side='right',fill='y')
        controller_vars=[]
        ttk.Label(ctl_inner,text='MGD field',font=('',9,'bold')).grid(row=0,column=0,sticky='w',padx=(2,6),pady=(0,4))
        ttk.Label(ctl_inner,text='Value(s)',font=('',9,'bold')).grid(row=0,column=1,columnspan=4,sticky='w',pady=(0,4))
        ttk.Label(ctl_inner,text='Status',font=('',9,'bold')).grid(row=0,column=5,sticky='w',padx=(8,4),pady=(0,4))
        ttk.Label(ctl_inner,text='Meaning / editing effect',font=('',9,'bold')).grid(row=0,column=6,sticky='w',padx=(8,4),pady=(0,4))
        ttk.Label(ctl_inner,text='Offset',font=('',9,'bold')).grid(row=0,column=7,sticky='w',padx=6,pady=(0,4))
        ctl_inner.columnconfigure(6,weight=1)
        crow=1
        for rr in recs:
            if rr is pos: continue
            if rr.size not in NUMERIC_SIZES: continue
            friendly,desc=describe_camera_value(rr.name)
            ttk.Label(ctl_inner,text=rr.name,width=23).grid(row=crow,column=0,sticky='nw',padx=(2,6),pady=3)
            rvars=[]
            for jj,v in enumerate(rr.values):
                sv=tk.StringVar(value=f'{v:.9g}'); rvars.append(sv)
                ttk.Entry(ctl_inner,textvariable=sv,width=12).grid(row=crow,column=1+jj,padx=2,pady=3,sticky='n')
            status=camera_value_status(rr.name)
            ttk.Label(ctl_inner,text=status,foreground='#555').grid(row=crow,column=5,sticky='nw',padx=(8,4),pady=3)
            ttk.Label(ctl_inner,text=f'{friendly} — {desc}',foreground='#555',wraplength=500,justify='left').grid(row=crow,column=6,sticky='nw',padx=(8,4),pady=3)
            ttk.Label(ctl_inner,text=f'0x{rr.value_offset:X}',foreground='#777').grid(row=crow,column=7,sticky='nw',padx=6,pady=3)
            controller_vars.append((rr,rvars))
            crow+=1

        # High-level stability controls. These do not guess the game's full camera math;
        # they scale only families whose names clearly describe dynamic offsets/ranges.
        dyn_box=ttk.LabelFrame(body,text='Broadcast stability / dynamic effects',padding=8)
        dyn_box.grid(row=9,column=0,columnspan=4,sticky='ew',pady=(0,10))
        dyn_box.columnconfigure(1,weight=1)
        zoom_pct=tk.DoubleVar(value=100.0)
        aim_pct=tk.DoubleVar(value=100.0)
        targety_pct=tk.DoubleVar(value=100.0)
        heading_pct=tk.DoubleVar(value=100.0)
        aimz_pct=tk.DoubleVar(value=100.0)
        basezoom_range_pct=tk.DoubleVar(value=100.0)
        distance_comp_pct=tk.DoubleVar(value=0.0)
        distance_comp_mode=tk.StringVar(value='inverse')
        pct_vars=[zoom_pct,aim_pct,targety_pct,heading_pct,aimz_pct,basezoom_range_pct,distance_comp_pct]
        labels=[
            ('Dynamic zoom / push-in',zoom_pct,'How much gameplay events may change framing. 0% = nearly no situational zoom; higher = stronger rim/target/play-event zoom.'),
            ('Aim freedom',aim_pct,'How far the camera may move its aim away from the normal target. Lower values keep the composition more static.'),
            ('Vertical target following',targety_pct,'How strongly player/ball vertical target movement influences aiming. Lower = steadier vertical composition.'),
            ('Horizontal rotation range',heading_pct,'How far left/right the camera may swivel. Lower = more static camera; 100% = original heading envelope.'),
            ('Target-height influence',aimz_pct,'How much target height/Z changes the aim point. Lower values reduce vertical reframing.'),
            ('Base framing range',basezoom_range_pct,'Width of the normal zoom range between zoom_min_* and zoom_max_*. 0% locks it near one framing; 100% keeps the original span.'),
            ('Long-distance framing compensation',distance_comp_pct,'Compensates base zoom when the physical camera is moved farther from court. Inverse mode is confirmed useful by in-game testing.'),
        ]
        for i,(lab,var,tip) in enumerate(labels):
            ttk.Label(dyn_box,text=lab,width=24).grid(row=i,column=0,sticky='w')
            ttk.Scale(dyn_box,from_=0,to=100,variable=var,orient='horizontal').grid(row=i,column=1,sticky='ew',padx=6)
            entry=ttk.Spinbox(dyn_box,from_=0,to=100,increment=1,textvariable=var,width=7)
            entry.grid(row=i,column=2,sticky='e')
            ttk.Label(dyn_box,text='%',width=2).grid(row=i,column=3,sticky='w',padx=(2,6))
            ttk.Label(dyn_box,text=tip,foreground='#666').grid(row=i,column=4,sticky='w',padx=(8,0))

        modebar=ttk.Frame(dyn_box)
        modebar.grid(row=7,column=0,columnspan=5,sticky='w',pady=(6,0))
        ttk.Label(modebar,text='Zoom convention:').pack(side='left')
        ttk.Radiobutton(modebar,text='Inverse (recommended)',variable=distance_comp_mode,value='inverse').pack(side='left',padx=(6,2))
        ttk.Radiobutton(modebar,text='Direct (legacy test)',variable=distance_comp_mode,value='direct').pack(side='left',padx=2)
        ttk.Radiobutton(modebar,text='Off',variable=distance_comp_mode,value='off').pack(side='left',padx=2)

        original_controller={id(rr):list(rr.values) for rr,_ in controller_vars}

        # Response controls map directly onto the damporientation family. These are kept
        # separate from framing because they change how quickly/loosely the camera follows
        # the target rather than where the camera is or how wide it frames the court.
        response_box=ttk.LabelFrame(body,text='Camera response / pan behavior',padding=8)
        response_box.grid(row=10,column=0,columnspan=4,sticky='ew',pady=(0,10))
        response_box.columnconfigure(4,weight=1)
        response_box.columnconfigure(1,weight=1)
        viscosity_pct=tk.DoubleVar(value=100.0)
        coupling_pct=tk.DoubleVar(value=100.0)
        maxvel_pct=tk.DoubleVar(value=100.0)
        tolerance_pct=tk.DoubleVar(value=100.0)
        netwindow_pct=tk.DoubleVar(value=100.0)
        response_vars=[viscosity_pct,coupling_pct,maxvel_pct,tolerance_pct,netwindow_pct]
        response_labels=[
            ('Pan damping / viscosity',viscosity_pct,'Higher = smoother, heavier rotation; lower = quicker response. Mainly changes how motion feels, not the allowed rotation range.'),
            ('Target-follow coupling',coupling_pct,'How strongly orientation is pulled toward the tracked target. Keep near 100% unless testing follow looseness.'),
            ('Maximum pan speed',maxvel_pct,'Caps how quickly the camera can rotate. Lower = fewer whip-pans and a more static broadcast feel.'),
            ('Pan correction tolerance',tolerance_pct,'Likely controls how much orientation error is tolerated before correction. Experimental.'),
            ('Basket-distance zoom window',netwindow_pct,'Experimental threshold window controlling when basket/net-distance-dependent zoom logic activates. Not the physical camera distance.'),
        ]
        for i,(lab,var,tip) in enumerate(response_labels):
            ttk.Label(response_box,text=lab,width=24).grid(row=i,column=0,sticky='w')
            ttk.Scale(response_box,from_=0,to=200,variable=var,orient='horizontal').grid(row=i,column=1,sticky='ew',padx=6)
            entry=ttk.Spinbox(response_box,from_=0,to=200,increment=1,textvariable=var,width=7)
            entry.grid(row=i,column=2,sticky='e')
            ttk.Label(response_box,text='%',width=2).grid(row=i,column=3,sticky='w',padx=(2,6))
            ttk.Label(response_box,text=tip,foreground='#666').grid(row=i,column=4,sticky='w',padx=(8,0))

        def set_response(visc=100,coup=100,maxv=100,tol=100,netwin=100):
            viscosity_pct.set(visc); coupling_pct.set(coup); maxvel_pct.set(maxv); tolerance_pct.set(tol); netwindow_pct.set(netwin)
        ttk.Label(response_box,text='These values can be adjusted with either the slider or the numeric percentage box. Net-distance remains experimental and is not included in Live Broadcast.',foreground='#555').grid(row=5,column=0,columnspan=5,sticky='w',pady=(7,0))

        def set_stability(zoom=100,aim=100,targety=100,heading=100,aimz=100,basezoom=100,distancecomp=0):
            zoom_pct.set(zoom); aim_pct.set(aim); targety_pct.set(targety); heading_pct.set(heading); aimz_pct.set(aimz); basezoom_range_pct.set(basezoom); distance_comp_pct.set(distancecomp)

        def restore_fields():
            for rr,rvars in controller_vars:
                vals=original_controller[id(rr)]
                for sv,v in zip(rvars,vals): sv.set(f'{v:.9g}')
            for sv,v in zip(pv,pos.values): sv.set(f'{v:.4f}')
            set_stability(); set_response()

        # User-tested broadcast preset. It changes controller behavior only; the arena-specific
        # Press Box XYZ remains whatever the user entered above.
        def set_live_broadcast():
            distance_comp_mode.set('inverse')
            set_stability(12,25,45,50,30,25,100)
            set_response(130,85,55,80,100)

        presetbar=ttk.Frame(dyn_box)
        presetbar.grid(row=8,column=0,columnspan=5,sticky='w',pady=(7,0))
        ttk.Button(presetbar,text='Live Broadcast',command=set_live_broadcast).pack(side='left')
        ttk.Button(presetbar,text='Restore Original Controls',command=lambda:(distance_comp_mode.set('off'),set_stability(100,100,100,100,100,100,0),set_response(100,100,100,100,100))).pack(side='left',padx=5)
        ttk.Button(presetbar,text='Restore MGD Fields',command=restore_fields).pack(side='left',padx=5)

        build_note=tk.StringVar(value='Live Broadcast is the current user-tested preset. It does not change the Press Box position, so each arena can keep its own XYZ coordinates.')
        ttk.Label(dyn_box,textvariable=build_note,foreground='#555').grid(row=9,column=0,columnspan=5,sticky='w',pady=(7,0))

        def transformed_controller_values(rr,rawvals,distance_ratio=1.0):
            name=rr.name.lower()
            vals=list(rawvals)
            if name=='maxzoomdiff' or name.startswith('zoomdiff_') or name.startswith('pitch_zoomdiff_'):
                f=zoom_pct.get()/100.0
                return [v*f for v in vals]
            if name.startswith('maxaimoffset_'):
                f=aim_pct.get()/100.0
                return [v*f for v in vals]
            if name.startswith('scaletargety_'):
                f=targety_pct.get()/100.0
                return [v*f for v in vals]
            if name=='aimtargetzratio':
                f=aimz_pct.get()/100.0
                return [v*f for v in vals]
            if name.startswith('zoom_min_') or name.startswith('zoom_max_'):
                # Collapse each min/max pair around its midpoint, then optionally apply
                # geometric distance compensation. This is intentionally experimental:
                # it preserves the MGD's native zoom convention rather than claiming FOV units.
                suffix=name.rsplit('_',1)[1] if '_' in name else ''
                mate_name=('zoom_max_'+suffix) if name.startswith('zoom_min_') else ('zoom_min_'+suffix)
                mate_pair=next(((x,rv) for x,rv in controller_vars if x.name.lower()==mate_name),None)
                if mate_pair and len(vals)==1 and len(mate_pair[1])==1:
                    mate_value=float(mate_pair[1][0].get())
                    lo=rawvals[0] if name.startswith('zoom_min_') else mate_value
                    hi=mate_value if name.startswith('zoom_min_') else rawvals[0]
                    mid=(lo+hi)/2.0
                    half=(hi-lo)/2.0*(basezoom_range_pct.get()/100.0)
                    out=mid-half if name.startswith('zoom_min_') else mid+half
                    p=distance_comp_pct.get()/100.0
                    ratio=max(0.01,distance_ratio)
                    mode=distance_comp_mode.get()
                    target=1.0 if mode=='off' else ((1.0/ratio) if mode=='inverse' else ratio)
                    comp=1.0 + p*(target-1.0)
                    return [out*comp]
                p=distance_comp_pct.get()/100.0
                ratio=max(0.01,distance_ratio)
                mode=distance_comp_mode.get()
                target=1.0 if mode=='off' else ((1.0/ratio) if mode=='inverse' else ratio)
                comp=1.0 + p*(target-1.0)
                return [v*comp for v in vals]
            if name.startswith('orientationvisc'):
                return [v*(viscosity_pct.get()/100.0) for v in vals]
            if name.startswith('orientationcoup'):
                return [v*(coupling_pct.get()/100.0) for v in vals]
            if name.startswith('orientationmaxv'):
                return [v*(maxvel_pct.get()/100.0) for v in vals]
            if name.startswith('orientationtole'):
                return [v*(tolerance_pct.get()/100.0) for v in vals]
            if name.startswith('hmin_') or name.startswith('hmax_'):
                # Pair matching hmin_N/hmax_N and narrow around midpoint.
                suffix=name.split('_',1)[1] if '_' in name else ''
                mate_name=('hmax_'+suffix) if name.startswith('hmin_') else ('hmin_'+suffix)
                mate_pair=next(((x,rv) for x,rv in controller_vars if x.name.lower()==mate_name),None)
                if mate_pair and len(vals)==1 and len(mate_pair[1])==1:
                    mate_value=float(mate_pair[1][0].get())
                    lo=rawvals[0] if name.startswith('hmin_') else mate_value
                    hi=mate_value if name.startswith('hmin_') else rawvals[0]
                    mid=(lo+hi)/2.0; half=(hi-lo)/2.0*(heading_pct.get()/100.0)
                    return [mid-half if name.startswith('hmin_') else mid+half]
            return vals

        def vec(vars_): return tuple(float(x.get()) for x in vars_)
        def calc():
            try:
                old=tuple(pos.values); new=vec(pv); tgt=vec(tv)
                def dist(a,b): return math.sqrt(sum((a[i]-b[i])**2 for i in range(3)))
                def elev(a,b):
                    dz=b[2]-a[2]; ground=math.hypot(b[0]-a[0],b[1]-a[1]); return math.degrees(math.atan2(dz,ground))
                d0=dist(old,tgt); d1=dist(new,tgt); ratio=d1/d0 if d0>1e-9 else 1.0
                # For a pinhole camera, preserving subject scale requires focal length ~= distance ratio.
                olde=elev(old,tgt); newe=elev(new,tgt)
                # basket span angle is a useful metric independent of MGD's unknown zoom convention
                def span(a):
                    va=(-netxv-a[0],0-a[1],5-a[2]); vb=(netxv-a[0],0-a[1],5-a[2])
                    da=math.sqrt(sum(x*x for x in va)); db=math.sqrt(sum(x*x for x in vb))
                    dot=sum(va[i]*vb[i] for i in range(3))/(da*db) if da*db else 1
                    dot=max(-1,min(1,dot)); return math.degrees(math.acos(dot))
                s0=span(old); s1=span(new)
                metrics.set(f'Distance to aim target: {d0:.2f} → {d1:.2f}  (×{ratio:.3f})\nElevation angle to aim target: {olde:.2f}° → {newe:.2f}°\nAngular span between baskets: {s0:.2f}° → {s1:.2f}°\nBlender framing suggestion: multiply focal length by ~{ratio:.3f} to preserve the old subject scale.\nLatest in-game test indicates NBA Live zoom likely runs opposite to focal length. Inverse compensation at 100% therefore scales zoom_min/max by ~×{(1.0/ratio if ratio else 1.0):.3f}; Direct mode retains the earlier ×{ratio:.3f} experiment.')
                return old,new,tgt,ratio
            except Exception as e:
                metrics.set(f'Invalid value: {e}'); return None
        for sv in pv+tv: sv.trace_add('write',lambda *_:calc())
        calc()

        def apply_position():
            got=calc()
            if not got:return
            _,new,_,_=got
            self.mgd.write_record(pos,new)
            # Stay on Press Box after rebuilding; otherwise ttk.Notebook defaults to
            # AmbientCamera_F and makes the edit appear to have disappeared.
            self.refresh(commit_pending=False,target_block=block)
            for sv,v in zip(current_vars,new): sv.set(f'{v:.4f}')
            messagebox.showinfo('Position applied','Updated the Press Box position in memory. The main editor remains on the Press Box tab.\n\nUse Save/Save As to write the MGD.')

        def apply_all():
            got=calc()
            if not got:return
            _,new,_,ratio=got
            try:
                parsed=[]
                for rr,rvars in controller_vars:
                    vals=[float(v.get()) for v in rvars]
                    if len(vals)*4 != rr.size:
                        raise ValueError(f'{rr.name}: wrong component count')
                    vals=transformed_controller_values(rr,vals,ratio)
                    parsed.append((rr,vals))
            except Exception as e:
                messagebox.showerror('Invalid controller value',str(e)); return
            self.mgd.write_record(pos,new)
            for rr,vals in parsed: self.mgd.write_record(rr,vals)
            # Reflect the actual transformed values in this dialog as well as the main editor.
            for rr,vals in parsed:
                pair=next(((r,rv) for r,rv in controller_vars if r is rr),None)
                if pair:
                    for sv,v in zip(pair[1],vals): sv.set(f'{v:.9g}')
                original_controller[id(rr)]=list(vals)
            self.refresh(commit_pending=False,target_block=block)
            for sv,v in zip(current_vars,new): sv.set(f'{v:.4f}')
            set_stability()
            messagebox.showinfo('Profile applied',f'Updated Press Box position plus {len(parsed)} controller record(s) in memory.\n\nStability percentages were baked into the relevant zoom/aim/target/heading values. Use Save/Save As to write the MGD.')

        def apply_framing_only():
            got=calc()
            if not got:return
            _,_,_,ratio=got
            try:
                parsed=[]
                for rr,rvars in controller_vars:
                    name=rr.name.lower()
                    if not (name.startswith('zoom_min_') or name.startswith('zoom_max_')):
                        continue
                    vals=[float(v.get()) for v in rvars]
                    vals=transformed_controller_values(rr,vals,ratio)
                    parsed.append((rr,vals))
            except Exception as e:
                messagebox.showerror('Invalid zoom value',str(e)); return
            for rr,vals in parsed:
                self.mgd.write_record(rr,vals)
                pair=next(((r,rv) for r,rv in controller_vars if r is rr),None)
                if pair:
                    for sv,v in zip(pair[1],vals): sv.set(f'{v:.9g}')
                original_controller[id(rr)]=list(vals)
            self.refresh(commit_pending=False,target_block=block)
            set_stability()
            messagebox.showinfo('Framing applied',f'Updated {len(parsed)} base zoom record(s) only. Position, heading, aim, damping and situational zoom values were left untouched.\n\nUse Save/Save As to write the MGD.')

        def apply_broadcast_profile():
            """Apply a coherent Press Box build without rewriting unrelated controller records.

            This intentionally touches only the families we have tested or can classify from names:
            position, base zoom, dynamic zoom offsets, aim offsets, vertical targeting and heading limits.
            Orientation response values are included in the broadcast build. zoom_netdist thresholds remain
            separate because their runtime meaning is still experimental.
            """
            got=calc()
            if not got:return
            _,new,_,ratio=got
            allowed=lambda n:(
                n.startswith('zoom_min_') or n.startswith('zoom_max_') or
                n=='maxzoomdiff' or n.startswith('zoomdiff_') or n.startswith('pitch_zoomdiff_') or
                n.startswith('maxaimoffset_') or n.startswith('scaletargety_') or
                n=='aimtargetzratio' or n.startswith('hmin_') or n.startswith('hmax_') or
                n.startswith('orientationvisc') or n.startswith('orientationcoup') or
                n.startswith('orientationmaxv') or n.startswith('orientationtole')
            )
            try:
                parsed=[]
                for rr,rvars in controller_vars:
                    name=rr.name.lower()
                    if not allowed(name):
                        continue
                    vals=[float(v.get()) for v in rvars]
                    vals=transformed_controller_values(rr,vals,ratio)
                    parsed.append((rr,vals))
            except Exception as e:
                messagebox.showerror('Invalid broadcast profile value',str(e)); return
            self.mgd.write_record(pos,new)
            for rr,vals in parsed:
                self.mgd.write_record(rr,vals)
                pair=next(((r,rv) for r,rv in controller_vars if r is rr),None)
                if pair:
                    for sv,v in zip(pair[1],vals): sv.set(f'{v:.9g}')
                original_controller[id(rr)]=list(vals)
            self.refresh(commit_pending=False,target_block=block)
            for sv,v in zip(current_vars,new): sv.set(f'{v:.4f}')
            set_stability()
            messagebox.showinfo('Broadcast profile applied',
                f'Updated Press Box position plus {len(parsed)} classified broadcast-controller record(s).\n\n'
                'Included orientation damping/coupling/max-velocity/tolerance. zoom_netdist thresholds remain untouched.\n'
                'Use Save/Save As to write the MGD.')

        def transformed_netdist_values(rr,rawvals):
            name=rr.name.lower()
            if not (name.startswith('zoom_netdist_mi') or name.startswith('zoom_netdist_ma')) or len(rawvals)!=1:
                return list(rawvals)
            is_min=name.startswith('zoom_netdist_mi')
            mate_name='zoom_netdist_ma' if is_min else 'zoom_netdist_mi'
            mate_pair=next(((x,rv) for x,rv in controller_vars if x.name.lower().startswith(mate_name)),None)
            if not mate_pair or len(mate_pair[1])!=1:
                return list(rawvals)
            mate=float(mate_pair[1][0].get())
            lo=rawvals[0] if is_min else mate
            hi=mate if is_min else rawvals[0]
            mid=(lo+hi)/2.0
            half=(hi-lo)/2.0*(netwindow_pct.get()/100.0)
            return [mid-half if is_min else mid+half]

        def _write_back_dialog_record(rr,vals):
            pair=next(((r,rv) for r,rv in controller_vars if r is rr),None)
            if pair:
                for sv,v in zip(pair[1],vals): sv.set(f'{v:.9g}')
            original_controller[id(rr)]=list(vals)

        def apply_response_only():
            families=('orientationvisc','orientationcoup','orientationmaxv','orientationtole')
            try:
                parsed=[]
                for rr,rvars in controller_vars:
                    n=rr.name.lower()
                    if not n.startswith(families): continue
                    vals=[float(v.get()) for v in rvars]
                    vals=transformed_controller_values(rr,vals,1.0)
                    parsed.append((rr,vals))
            except Exception as e:
                messagebox.showerror('Invalid response value',str(e)); return
            for rr,vals in parsed:
                self.mgd.write_record(rr,vals); _write_back_dialog_record(rr,vals)
            self.refresh(commit_pending=False,target_block=block)
            set_response()
            messagebox.showinfo('Response applied',f'Updated {len(parsed)} orientation-response record(s) only. Framing, target offsets and net-distance thresholds were left untouched.\n\nUse Save/Save As to write the MGD.')

        def apply_netdistance_test():
            try:
                parsed=[]
                for rr,rvars in controller_vars:
                    n=rr.name.lower()
                    if not (n.startswith('zoom_netdist_mi') or n.startswith('zoom_netdist_ma')): continue
                    vals=[float(v.get()) for v in rvars]
                    vals=transformed_netdist_values(rr,vals)
                    parsed.append((rr,vals))
            except Exception as e:
                messagebox.showerror('Invalid net-distance value',str(e)); return
            for rr,vals in parsed:
                self.mgd.write_record(rr,vals); _write_back_dialog_record(rr,vals)
            self.refresh(commit_pending=False,target_block=block)
            netwindow_pct.set(100)
            messagebox.showinfo('Net-distance test applied',f'Updated {len(parsed)} zoom_netdist threshold record(s) only. This control remains experimental.\n\nUse Save/Save As to write the MGD.')

        def export_compare():
            got=calc()
            if not got:return
            old,new,tgt,ratio=got
            p=filedialog.asksaveasfilename(defaultextension='.py',initialfile='PressBox_Comparison.py',filetypes=[('Blender Python','*.py')])
            if not p:return
            self._write_pressbox_compare_script(p,block,old,new,tgt,netxv,ratio,recs)
            messagebox.showinfo('Blender export','Wrote a Press Box comparison rig.\n\nRun it from Blender Scripting. It creates original/proposed cameras, a movable target, basket references, and a simple target animation.')

        buttons=ttk.Frame(body); buttons.grid(row=11,column=0,columnspan=4,sticky='ew',pady=(4,0))
        ttk.Button(buttons,text='Export Blender Comparison...',command=export_compare).pack(side='left')
        ttk.Button(buttons,text='Apply Position Only',command=apply_position).pack(side='left',padx=6)
        ttk.Button(buttons,text='Apply Framing Only',command=apply_framing_only).pack(side='left',padx=(0,6))
        ttk.Button(buttons,text='Apply Broadcast Build',command=apply_broadcast_profile).pack(side='left')
        ttk.Button(buttons,text='Apply Response Only',command=apply_response_only).pack(side='left',padx=6)
        ttk.Button(buttons,text='Apply Net-Distance Test',command=apply_netdistance_test).pack(side='left',padx=(0,6))
        ttk.Button(buttons,text='Close',command=win.destroy).pack(side='right')

    def _write_pressbox_compare_script(self,p,block,old,new,target,netx,ratio,recs):
        # Store controller values as Blender custom properties for side-by-side research.
        props={}
        for r in recs:
            if r.size in NUMERIC_SIZES and r.name.lower()!='position':
                props.setdefault(r.name,[]).append(tuple(r.values))
        lines=[
            'import bpy, math',
            'from mathutils import Vector',
            '',
            '# NBA Live Press Box comparison rig — generated by v0.3.5-alpha',
            '# Coordinates stay in NBA Live game space: X/Y floor plane, Z up.',
            '# Proposed lens scaling is geometric preview only; it is NOT an asserted MGD zoom conversion.',
            '',
            'def coll(name):',
            '    c=bpy.data.collections.get(name)',
            '    if c is None: c=bpy.data.collections.new(name); bpy.context.scene.collection.children.link(c)',
            '    return c',
            'def link(o,c): c.objects.link(o)',
            'def look(obj,t):',
            "    obj.rotation_euler=(Vector(t)-obj.location).to_track_quat('-Z','Y').to_euler()",
            "root=coll('NBA Press Box Study')",
            "helpers=coll('NBA Press Box Helpers')",
            f"target=bpy.data.objects.new('PB_Target',None); target.empty_display_type='SPHERE'; target.empty_display_size=1.25; target.location={tuple(target)!r}; link(target,helpers)",
            f"for x,n in [(-{float(netx)!r},'Basket_L'),({float(netx)!r},'Basket_R')]:",
            "    e=bpy.data.objects.new(n,None); e.empty_display_type='CUBE'; e.empty_display_size=1.0; e.location=(x,0,10.0); link(e,helpers)",
            "mesh=bpy.data.meshes.new('CourtRefMesh'); verts=[(-40,-25,0),(40,-25,0),(40,25,0),(-40,25,0)]; mesh.from_pydata(verts,[(0,1),(1,2),(2,3),(3,0)],[]); mesh.update(); court=bpy.data.objects.new('CourtRef_APPROX',mesh); link(court,helpers)",
            'def makecam(name,loc,lens):',
            "    d=bpy.data.cameras.new(name); o=bpy.data.objects.new(name,d); link(o,root); o.location=loc; d.lens=lens; d.display_size=4; look(o,target.location); return o",
            f"old=makecam('PressBox_Original',{tuple(old)!r},50.0)",
            f"new=makecam('PressBox_Proposed',{tuple(new)!r},{50.0*ratio!r})",
            f"new['preview_distance_ratio']={ratio!r}",
            "new['preview_note']='Lens scaled by distance ratio only to preserve approximate subject size'",
            f"old['nba_source_block']={block!r}; new['nba_source_block']={block!r}",
            '',
            '# Keep the target movable: drivers/constraints make both cameras continuously aim at it.',
            "for o in (old,new):",
            "    c=o.constraints.new(type='TRACK_TO'); c.target=target; c.track_axis='TRACK_NEGATIVE_Z'; c.up_axis='UP_Y'",
            '',
            '# Animate a schematic live-play target from basket to center to basket.',
            f"target.location=(-{float(netx)!r},0,5); target.keyframe_insert(data_path='location',frame=1)",
            "target.location=(0,0,5); target.keyframe_insert(data_path='location',frame=60)",
            f"target.location=({float(netx)!r},0,5); target.keyframe_insert(data_path='location',frame=120)",
            "bpy.context.scene.frame_start=1; bpy.context.scene.frame_end=120",
            "bpy.context.scene.camera=new",
            '',
            '# MGD Press Box controller values, retained on the proposed object for research:',
        ]
        for name, vals_list in props.items():
            safe=name.replace("'",'_')
            if len(vals_list)==1:
                val=vals_list[0][0] if len(vals_list[0])==1 else vals_list[0]
                lines.append(f"new[{safe!r}]={val!r}")
            else:
                for i,valtuple in enumerate(vals_list):
                    val=valtuple[0] if len(valtuple)==1 else valtuple
                    lines.append(f"new[{(safe+'_'+str(i))!r}]={val!r}")
        lines += [
            "print('Press Box study created. Move PB_Target or scrub frames 1-120; compare Original vs Proposed camera view.')",
        ]
        open(p,'w',encoding='utf-8').write('\n'.join(lines))

    def _choose_camera_block(self):
        if not self.mgd:return None
        blocks=[]
        for r in self.mgd.records:
            if r.block not in blocks: blocks.append(r.block)
        if not blocks:return None
        win=tk.Toplevel(self.root); win.title('Choose Camera'); win.transient(self.root); win.grab_set(); win.resizable(False,False)
        body=ttk.Frame(win,padding=12); body.pack(fill='both',expand=True)
        ttk.Label(body,text='Camera block to export:').grid(row=0,column=0,columnspan=2,sticky='w',pady=(0,6))
        choice=tk.StringVar(value=blocks[0])
        cb=ttk.Combobox(body,textvariable=choice,values=blocks,state='readonly',width=34); cb.grid(row=1,column=0,columnspan=2,sticky='ew'); cb.focus_set()
        result={'value':None}
        def ok(): result['value']=choice.get(); win.destroy()
        def cancel(): win.destroy()
        ttk.Button(body,text='Export',command=ok).grid(row=2,column=0,sticky='e',padx=(0,4),pady=(10,0))
        ttk.Button(body,text='Cancel',command=cancel).grid(row=2,column=1,sticky='w',padx=(4,0),pady=(10,0))
        win.bind('<Return>',lambda e:ok()); win.bind('<Escape>',lambda e:cancel())
        self.root.wait_window(win)
        return result['value']

    def _collect_blender_cameras(self, selected_block=None):
        groups={}
        for r in self.mgd.records:
            if selected_block is None or r.block==selected_block:
                groups.setdefault(r.block,[]).append(r)

        cams=[]; notes=[]; ranges={}

        def first(flat, name, size=None):
            nl=name.lower()
            return next((x for x in flat if x.name.lower()==nl and (size is None or x.size==size)),None)

        def scalar(flat, name):
            r=first(flat,name,4)
            return r.values[0] if r else None

        def scalars_prefix(flat, prefix):
            pl=prefix.lower()
            return [r.values[0] for r in flat if r.size==4 and r.name.lower().startswith(pl)]

        def midpoint(vals):
            return (min(vals)+max(vals))*0.5 if vals else None

        for block,flat in groups.items():
            used=set(); before=len(cams)

            # Explicit serialized pose pairs used by ambient/cutscene/special cameras.
            pair_rules=[
                ('position','orientation'),
                ('freeThrowPos','freeThrowOri'),
                ('tipCamPos','tipCamOri'),
            ]
            for r in flat:
                if r.size!=12: continue
                low=r.name.lower()
                paired=None
                for pp,op in pair_rules:
                    ppl=pp.lower(); opl=op.lower()
                    if low.startswith(ppl):
                        suffix=low[len(ppl):]
                        paired=next((x for x in flat if x.size==12 and x.name.lower()==opl+suffix),None)
                        break
                if paired:
                    z=None
                    # Ambient camera convention: position2_a/orientation2_a/zoom2_a.
                    if low.startswith('position'):
                        suffix=low[len('position'):]
                        zr=next((x for x in flat if x.size==4 and x.name.lower()=='zoom'+suffix),None)
                        z=zr.values[0] if zr else None
                    cams.append({'block':block,'label':r.name,'pos':tuple(r.values),'rot':tuple(paired.values),
                                 'zoom':z,'kind':'serialized','dynamic':False,'animate':None})
                    used.add(id(r)); used.add(id(paired))

            # VectorN/EulerN/FloatN convention.
            for r in flat:
                if r.size==12 and r.name.startswith('Vector'):
                    suffix=r.name[6:]
                    rr=next((x for x in flat if x.name=='Euler'+suffix and x.size==12),None)
                    fl=next((x for x in flat if x.name=='Float'+suffix and x.size==4),None)
                    if rr:
                        cams.append({'block':block,'label':r.name,'pos':tuple(r.values),'rot':tuple(rr.values),
                                     'zoom':fl.values[0] if fl else None,'kind':'serialized','dynamic':False,'animate':None})
                        used.add(id(r)); used.add(id(rr))

            # Base positions whose final orientation is calculated by the game.
            for base_name in ('CameraPosition','position'):
                r=first(flat,base_name,12)
                if r and id(r) not in used:
                    cams.append({'block':block,'label':r.name,'pos':tuple(r.values),'rot':None,'zoom':None,
                                 'kind':'dynamic-base','dynamic':True,'animate':None})
                    used.add(id(r))

            # Reconstruct a representative point for range-driven gameplay cameras.
            # These are explicitly marked ESTIMATED; they are not claims about a literal stored pose.
            xmins=scalars_prefix(flat,'xposmin_') or scalars_prefix(flat,'xmin_')
            xmaxs=scalars_prefix(flat,'xposmax_') or scalars_prefix(flat,'xmax_')
            ymins=scalars_prefix(flat,'ymin_')
            ymaxs=scalars_prefix(flat,'ymax_')
            zmins=scalars_prefix(flat,'zposmin_') or scalars_prefix(flat,'zmin_')
            zmaxs=scalars_prefix(flat,'zposmax_') or scalars_prefix(flat,'zmax_')

            # Baseline files use yposmax_min/max as a dynamic lateral envelope rather than ymin/ymax.
            if not ymins and not ymaxs:
                ya=scalars_prefix(flat,'yposmax_min_')
                yb=scalars_prefix(flat,'yposmax_max_')
                if ya or yb:
                    # Camera can operate on either side; center is the safest representative Y.
                    ymid=0.0
                    yextent=max([abs(v) for v in ya+yb],default=0.0)
                    ymins=[-yextent]; ymaxs=[yextent]
                else:
                    ymid=None
            else:
                ymid=midpoint(ymins+ymaxs)

            if xmins and xmaxs and zmins and zmaxs and not any(c['block']==block and c['kind']=='dynamic-base' for c in cams):
                xmid=midpoint(xmins+xmaxs)
                if ymid is None: ymid=0.0
                zmid=midpoint(zmins+zmaxs)
                pmins=scalars_prefix(flat,'pitchmin_') or scalars_prefix(flat,'pitch_min_')
                pmaxs=scalars_prefix(flat,'pitchmax_') or scalars_prefix(flat,'pitch_max_')
                hmins=scalars_prefix(flat,'headingmin')
                hmaxs=scalars_prefix(flat,'headingmax')
                pitch=midpoint(pmins+pmaxs) if (pmins or pmaxs) else None
                heading=midpoint(hmins+hmaxs) if (hmins or hmaxs) else None
                rot=None if pitch is None and heading is None else (0.0,pitch or 0.0,heading or 0.0)
                amin=(midpoint(xmins), midpoint(ymins) if ymins else ymid, midpoint(zmins))
                amax=(midpoint(xmaxs), midpoint(ymaxs) if ymaxs else ymid, midpoint(zmaxs))
                cams.append({'block':block,'label':'RepresentativeRange','pos':(xmid,ymid,zmid),'rot':rot,'zoom':None,
                             'kind':'estimated-range','dynamic':True,'animate':(amin,amax)})
                ranges[block]={'min':amin,'max':amax}

            if len(cams)==before:
                notes.append(block)
        return cams,notes,ranges

    def _write_blender_script(self,p,cams,notes,ranges,source_label):
        # The generated scene intentionally keeps NBA Live coordinates unchanged: X/Y court plane, Z up.
        # That makes numeric comparisons with the MGD straightforward while coordinate semantics are researched.
        lines=[
            "import bpy, math",
            "from mathutils import Vector",
            "",
            "# Generated by NBA Live MGD Camera Editor v0.3.1-alpha",
            "# NBA Live coordinates are kept 1:1 (X/Y floor plane, Z vertical).",
            "# Serialized Euler values are provisionally treated as XYZ radians.",
            "# ESTIMATED/RANGE cameras are visual aids reconstructed from limits, not literal game poses.",
            "# Preview keyframes show the discovered motion envelope only; they are NOT recovered game animation.",
            "",
            "def ensure_collection(name):",
            "    c=bpy.data.collections.get(name)",
            "    if c is None:",
            "        c=bpy.data.collections.new(name); bpy.context.scene.collection.children.link(c)",
            "    return c",
            "",
            "def link_obj(obj, coll):",
            "    coll.objects.link(obj)",
            "",
            "def look_at(obj, target=(0.0,0.0,5.0)):",
            "    direction=Vector(target)-obj.location",
            "    if direction.length > 1e-6:",
            "        obj.rotation_euler=direction.to_track_quat('-Z','Y').to_euler()",
            "",
            "cams=ensure_collection('NBA Cameras')",
            "helpers=ensure_collection('NBA Camera Helpers')",
            "",
            "# Schematic game-space court reference. netx=40 in several gameplay camera controllers,",
            "# so +/-40 is used as the baseline reference; width is a visual aid only.",
            "mesh=bpy.data.meshes.new('NBA_Court_Reference_Mesh')",
            "verts=[(-40,-25,0),(40,-25,0),(40,25,0),(-40,25,0)]",
            "mesh.from_pydata(verts,[(0,1),(1,2),(2,3),(3,0)],[]); mesh.update()",
            "court=bpy.data.objects.new('NBA_Court_Reference_APPROX',mesh); link_obj(court,helpers)",
            "court['nba_note']='Approximate game-space reference, not a decoded court asset'",
            "target=bpy.data.objects.new('NBA_Target_Reference',None); target.empty_display_type='SPHERE'; target.empty_display_size=1.0; target.location=(0,0,5); link_obj(target,helpers)",
            "",
        ]
        for c in cams:
            block,label,pos,rot,z,kind,dynamic,anim=(c[k] for k in ('block','label','pos','rot','zoom','kind','dynamic','animate'))
            nm=(block+' '+label).replace("'",'_')
            lines += [
                f"data=bpy.data.cameras.new({nm!r})",
                f"obj=bpy.data.objects.new({nm!r},data)",
                "link_obj(obj,cams)",
                f"obj.location={tuple(pos)!r}",
                "obj.rotation_mode='XYZ'",
            ]
            if rot is not None and kind=='serialized':
                lines += [f"obj.rotation_euler={tuple(rot)!r}"]
            else:
                lines += ["look_at(obj,target.location)"]
            lines += [
                "data.display_size=3.0",
                f"obj['nba_source_block']={block!r}",
                f"obj['nba_source_record']={label!r}",
                f"obj['nba_preview_kind']={kind!r}",
                f"obj['nba_dynamic_orientation']={bool(dynamic)!r}",
            ]
            if rot is not None:
                lines += [f"obj['nba_raw_euler']={tuple(rot)!r}"]
            if z is not None:
                lines += [f"obj['nba_zoom_or_float']={float(z)!r}"]
            if anim is not None:
                amin,amax=anim
                lines += [
                    "obj['nba_preview_animation']='range envelope only'",
                    f"obj.location={tuple(amin)!r}; look_at(obj,target.location); obj.keyframe_insert(data_path='location',frame=1); obj.keyframe_insert(data_path='rotation_euler',frame=1)",
                    f"obj.location={tuple(pos)!r}; look_at(obj,target.location); obj.keyframe_insert(data_path='location',frame=60); obj.keyframe_insert(data_path='rotation_euler',frame=60)",
                    f"obj.location={tuple(amax)!r}; look_at(obj,target.location); obj.keyframe_insert(data_path='location',frame=120); obj.keyframe_insert(data_path='rotation_euler',frame=120)",
                    "bpy.context.scene.frame_start=1; bpy.context.scene.frame_end=max(bpy.context.scene.frame_end,120)",
                ]
            lines += [""]
        if notes:
            lines += ["# Blocks with no reconstructable position yet:"]
            for n in notes: lines += [f"#   {n}"]
        lines += [
            "if len(cams.objects):",
            "    bpy.context.scene.camera=next((o for o in cams.objects if o.type=='CAMERA'),None)",
            f"print('Imported {len(cams)} NBA camera/preset objects from {source_label}')",
        ]
        open(p,'w',encoding='utf-8').write('\n'.join(lines))

    def export_blender_selected(self):
        if not self.mgd:return
        if not self.commit():return
        block=self._choose_camera_block()
        if not block:return
        cams,notes,ranges=self._collect_blender_cameras(block)
        if not cams:
            messagebox.showwarning('No static camera pose',f'{block} has no directly serialized position/orientation pair or base position that can be previewed yet.\n\nIts camera position appears to be calculated dynamically from limits/targets.')
            return
        p=filedialog.asksaveasfilename(defaultextension='.py',initialfile=re.sub(r'[^A-Za-z0-9_.-]+','_',block)+'.py',filetypes=[('Blender Python','*.py')])
        if not p:return
        self._write_blender_script(p,cams,notes,ranges,block)
        dynamic=sum(1 for c in cams if c['dynamic'])
        estimated=sum(1 for c in cams if c['kind']=='estimated-range')
        extra=(f'\n{dynamic} dynamic/derived object(s); {estimated} range-derived representative pose(s).' if dynamic else '')
        messagebox.showinfo('Blender export',f'Wrote {len(cams)} camera/preset object(s) for {block}.{extra}\n\nRun the .py file from Blender Scripting.')

    def export_blender_all(self):
        if not self.mgd:return
        if not self.commit():return
        cams,notes,ranges=self._collect_blender_cameras(None)
        p=filedialog.asksaveasfilename(defaultextension='.py',filetypes=[('Blender Python','*.py')])
        if not p:return
        self._write_blender_script(p,cams,notes,ranges,'all camera blocks')
        messagebox.showinfo('Blender export',f'Wrote {len(cams)} camera/preset object(s).\n\nRun the .py file from Blender Scripting.\nRange-driven cameras include a clearly marked 1-60-120 preview envelope; this is not recovered game animation.')

if __name__=='__main__':
    root=tk.Tk(); App(root); root.mainloop()

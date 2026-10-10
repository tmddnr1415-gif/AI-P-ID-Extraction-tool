import sys, collections
sys.path.insert(0,'/home/user/AI-P-ID-Extraction-tool'); sys.path.insert(0,'/home/user/AI-P-ID-Extraction-tool/app/engine')
import pidcache
for name,pdf in [("AL NOUF1","data/pid_total.pdf"),("TC2","data/TC2_260821.pdf"),("QFE","data/QFE_260326.pdf")]:
    _d, pages = pidcache.load_pages('/home/user/AI-P-ID-Extraction-tool/'+pdf)
    hist=collections.Counter(); n=0
    for pc in pages:
        if not pc.analysis_scope: continue
        for line in pidcache.same_lines(list(pc.words)):
            h=max(r.y1-r.y0 for r,_ in line) or 1
            for (r1,_),(r2,_) in zip(line,line[1:]):
                g=(r2.x0-r1.x1)/h
                hist[min(round(g*4)/4, 12)]+=1; n+=1
    print(name,'pairs',n)
    print('  gap/h histogram (0.25 bins, capped 12):', ' '.join(f"{k}:{v}" for k,v in sorted(hist.items())))

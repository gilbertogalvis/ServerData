import numpy as np

from itertools import groupby

from scipy.integrate   import cumtrapz
from scipy.interpolate import interp1d
from scipy.signal import savgol_filter

from horsetoolkit.StiffnessAnalyzer.utils import get_low, get_high


# ---------------------------------------------------------
# energy

# get_energy = lambda x: np.sum(x**2)
# get_low_energy = lambda x,fs,cut: np.sum(get_low(x,fs,cut)**2)
# # get_high_energy = lambda x,fs,cut: np.sum(get_high(x,fs,cut)**2)
# get_high_energy = lambda x,fs,cut: np.sum(np.abs(get_high(x,fs,cut)))
# norm_energy = lambda x, E, f: np.sqrt( E / get_energy(x) ) * x * f
# norm_low_energy = lambda x, E, fs, cut, f: np.sqrt( E / get_low_energy(x, fs, cut) ) * x * f
# norm_high_energy = lambda x, E, fs, cut, f: np.sqrt( E / get_high_energy(x, fs, cut) ) * x * f

# get_mag_energy = lambda x: np.sum( np.sqrt( np.sum( x**2, axis=1 ) ) )

# ---------------------------------------------------------
# 2D rotations

def get_2D_rotation_matrix(yaw):
    return np.array([
        [ np.cos(yaw), -np.sin(yaw) ],
        [ np.sin(yaw),  np.cos(yaw) ],
    ])

def do_2D_rotation( x, y, yaw, as_dict=False ):
    _do_2D_rotation_ = lambda x, y, yaw: np.dot(np.linalg.inv( get_2D_rotation_matrix( yaw ) ), [x, y])
    cog = np.array([ _do_2D_rotation_(xi, yi, ywi) for xi, yi, ywi in zip( x, y, yaw*np.pi/180. ) ])
    
    if as_dict:
        cog = {'x':cog[:,0], 'y':cog[:,1]}
    
    return cog

# ---------------------------------------------------------
# filtering

def get_energy(x, **kwargs):
    if kwargs.get('factor', 1) == 0: return 0
    
    filter = kwargs.get('filter', 'h')
    fs = kwargs.get('fs', 200)
    cut = kwargs.get('cut', 0.025) 
    lnorm = kwargs.get('lnorm', 2)
    
    print(kwargs)
    print(filter, fs, cut, lnorm)
    
    lnorm_list = [
        np.max,
        np.abs,
        lambda x: x**2,
    ]
    filter_dict = dict(
        h = get_high,
        l = get_low,
        none = lambda x, fs, cut: x,
    )
    
    return np.sum( lnorm_list[lnorm]( filter_dict[filter](x, fs, cut) ) )

base_energies = dict(
    walk = dict(
        x = dict(rider=3.229767507539319e-05, horse=1.5386295701439644e-05),
        y = dict(rider=0.00012270714468073785, horse=0.00011245085714256052),
        z = dict(rider=9.023666345604323e-05, horse=0.00016556820598973053),
    ),
    trot = dict(
        x = dict(rider=6.621229640343991e-05, horse=6.84486961166495e-05),
        y = dict(rider=0.0008848617145076344, horse=6.694872082309733e-05),
        z = dict(rider=0.002079280300032458, horse=0.001972065585653065),
    ),
    gallop = dict(
        x = dict(rider=0.0002003555365142044, horse=0.0002530333398786959),
        y = dict(rider=0.0006910085462722564, horse=0.0005858080570065349),
        z = dict(rider=0.006415908507151783, horse=0.004001713843307231),
    ),
)
base_factors = dict(
    walk=dict(
        x = dict(rider=10.0, horse=10.0),
        y = dict(rider=10.0, horse=10.0),
        z = dict(rider=3.0, horse=3.0)
    ),
    trot=dict(
        # x = dict(rider=10.0, horse=50.0),
        # y = dict(rider=10.0, horse=50.0),
        x = dict(rider=10.0, horse=100.0),
        y = dict(rider=10.0, horse=10.0),
        z = dict(rider=5.0, horse=5.0)
    ),
    gallop=dict(
        x = dict(rider=10.0, horse=10.0),
        y = dict(rider=10.0, horse=10.0),
        z = dict(rider=5.0, horse=5.0)
    ),
    
)

def do_normalization(x, E, **kwargs):
    if E == 0: return x
    print(E)
    
    lnorm = kwargs.get('lnorm', 2)
    factor = kwargs.get('factor', 1)
    
    norm = E / get_energy(x, lnorm=lnorm, filter='none')
    norm = np.sqrt(norm) if lnorm==2 else norm
    
    return norm * x * factor

def _do_filtering_(x, FS, f, **do_norm):
    if not f: 
        return x
    
    # E = get_energy(x, **do_norm) if 'H' in f['name'] else 0
    
    if f['name'] == 'HPF':
        x = get_high( x, FS, f['cutoff'] )
    elif f['name'] == 'HSAVGOL':
        x -= savgol_filter( x, int( FS * ( 1 / f['cutoff'] ) ), 3 )
    
    elif f['name'] == 'LPF':
        x = get_low( x, FS, f['cutoff'] )
    elif f['name'] == 'LSAVGOL':
        x = savgol_filter( x, int( FS * ( 1 / f['cutoff'] ) ), 3 )
    
    # return do_normalization(x, E, **do_norm)
    return x

# ---------------------------------------------------------
# integrals

def do_cog_norm_by_gait(data, device='rider', do_norm=dict()):
    gait_items, start = [], 0
    d = device.lower().replace('back', 'horse')
    
    base_factors = do_norm.get('base_factors', None)
    base_energies = do_norm.get('base_energies', None)

    for key, group in groupby(data["gait"]):
        gait_items.append( (key, start, start+len(list(group))) )
        start = gait_items[-1][-1]
    
    for g, s, e in gait_items:
        if g=='stay': continue
        for a in ['x', 'y', 'z']:
            norm = (e-s+1) * base_factors[g][a][d] * base_energies[g][a][d] / np.sum( data[a][s:e]**2 )
            # norm = (e-s+1) * base_factors[g][a][d] * base_energies[g][a]['rider'] / np.sum( data[a][s:e]**2 )
            norm = np.sqrt(norm)
            
            data[a][s:e] *= norm
            
    return data
    

def do_integral(tracker, filters, **kwargs):
    device = kwargs.get('device', 'BACK')
    level = kwargs.get('level', 2)
    axis = kwargs.get('axis', ['x', 'y', 'z'])
    do_norm = kwargs.get('do_norm', dict())
    
    FS = tracker.cfg.SAMPLE_RATE
    integrated = { ax:tracker.acceleration[device][:,i].copy() for i,ax in enumerate(axis) }
    integrated['ts'] = tracker.timestamp[device].copy()
    
    for i,ax in enumerate(axis):
        integrated[ax] = _do_filtering_(integrated[ax], FS, f=filters.get('filter_in', False))
        
        for l in range(level):
            integrated[ax] = cumtrapz( integrated[ax], integrated['ts'], initial=0 )
            
            for k,f in filters.items():
                if k=='filter_in': continue
                if k=='filter_out' and l<level-1: continue
                
                integrated[ax] = _do_filtering_(integrated[ax], FS, f, **do_norm)
    
    # if (do_norm>0) and ('z' in axis):
    #     base_energy = get_energy(integrated['z'])
    #     print(base_energy)
    #     # print([ np.sum(get_low(integrated[a], FS, 0.025)**2) for a in axis])
    #     # for ax in ['x', 'y']:
    #     #     if not ax in axis: continue
    #     #     integrated[ax] = norm_energy(integrated[ax], base_energy, do_norm)
    #     print(get_mag_energy( np.array([integrated[a] for a in axis]).T ) )
    #     base_energy = get_mag_energy( np.array([integrated[a] for a in axis]).T )
    #     for a in axis:
    #         # integrated[a] = norm_energy(integrated[a], 500, do_norm)
    #         integrated[a] = norm_energy(integrated[a], base_energy, do_norm)
    #         # print(get_mag_energy(integrated))
    #         # print(get_high_energy(integrated[a], FS, 0.025))
    #         # integrated[a] = norm_energy(integrated[a], get_low_energy(integrated[a], FS, 0.5), do_norm)
    #         # integrated[a] = norm_energy(integrated[a], get_high_energy(integrated[a], FS, 0.025), do_norm)
    
    return integrated

def do_integral__(tracker, axis=['x', 'y', 'z'], sen='BACK', level=2, **cfg):
    cfg = { k0:cfg.get( k0, v0 ) for k0,v0 in cfg_integral.items() }
    cfg = { k0:{ k1:cfg[k0].get( k1, v1 ) for k1,v1 in v0.items() } for k0,v0 in cfg_integral.items() }
    
    FS = tracker.cfg.SAMPLE_RATE
    OUT = { ax:tracker.acceleration[sen][:,i].copy() for i,ax in enumerate(axis) }
    E = { ax:get_energy( OUT[ax] ) for i,ax in enumerate(axis) }
    OUT['ts'] = tracker.timestamp[sen].copy()
    
    cfg['filter'] = cfg['filter'] if 'filter' in cfg else cfg_integral['filter']
    cfg['filter_out'] = cfg['filter_out'] if 'filter_out' in cfg else cfg_integral['filter_out']
    
    for i,ax in enumerate(axis):
        
        for l in range(level):
            
            OUT[ax] = cumtrapz( OUT[ax], OUT['ts'], initial=0 )
            
            for k,f in cfg.items():
                # print(ax, l, k, f, FS)
                
                if k=='filter_out' and l<level-1:
                    # print('skipped')
                    # if l > -10:
                    #     OUT = { ax:np.sqrt( E[ax]/sum(OUT[ax]**2) ) * OUT[ax] for i,ax in enumerate(axis) }
                    #     OUT['ts'] = tracker.timestamp[sen].copy()
                    continue
                
                if f['name'] == 'HPF':
                    E = get_energy( OUT[ax] )
                    OUT[ax] = get_high( OUT[ax], FS, f['cutoff'] )
                    OUT[ax] = norm_energy( OUT[ax], E )
                elif f['name'] == 'HSAVGOL':
                    E = get_energy( OUT[ax] )
                    OUT[ax] -= savgol_filter( OUT[ax], int( FS * ( 1 / f['cutoff'] ) ), 3 )
                    OUT[ax] = norm_energy( OUT[ax], E )
                
                elif f['name'] == 'LPF':
                    # E = get_energy( OUT[ax] )
                    OUT[ax] = get_low( OUT[ax], FS, f['cutoff'] )
                    # OUT[ax] = norm_energy( OUT[ax], E )
                elif f['name'] == 'LSAVGOL':
                    # E = get_energy( OUT[ax] )
                    OUT[ax] = savgol_filter( OUT[ax], int( FS * ( 1 / f['cutoff'] ) ), 3 )
                    # OUT[ax] = norm_energy( OUT[ax], E )
    
    return OUT



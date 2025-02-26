from datetime import datetime as dt
from numpy import array

class CoGconfig:
    def __init__(self, **kwargs):
        
        self.FMT = '%H:%M:%S.%f'
        self.TS_START = dt(1900,1,1)

        self.integral_filters = {
            'filter': {
                'name': 'HPF', # | 'NONE' | 'HPF' | 'HSAVGOL' |
                'cutoff': 1.0, # [Hz]
            }, 
            
            'filter_out': {
                'name': 'LSAVGOL', # | 'NONE' | 'LPF' | 'LSAVGOL' |
                'cutoff': 5.0, # [Hz]
            },
            
            'filter_in': {
                'name': 'None', 
                'cutoff': 1.0, # 1 Hz
            }
        }
        
        self.devices      = kwargs.get( 'devices', ['BACK', 'RIDER'] )
        self.axis         = kwargs.get( 'axis', ['x', 'y', 'z'] )
        self.level        = kwargs.get( 'level', 2 )
        self.interval     = kwargs.get( 'interval', False )
        self.yaw_offset   = kwargs.get( 'yaw_offset', 0 )
        self.fs_animation = kwargs.get( 'fs_animation', 40 )
        
        self.do_norm = kwargs.get( 'do_norm', dict(
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
            ),
            base_factors = dict(
                walk=dict(
                    x = dict(rider=10.0, horse=10.0),
                    y = dict(rider=10.0, horse=10.0),
                    z = dict(rider=4.0, horse=4.0)
                ),
                trot=dict(
                    # x = dict(rider=10.0, horse=50.0),
                    # y = dict(rider=10.0, horse=50.0),
                    # x = dict(rider=10.0, horse=100.0),
                    # y = dict(rider=10.0, horse=10.0),
                    # z = dict(rider=4.0, horse=4.0)
                    x = dict(rider=10.0, horse=20.0),
                    y = dict(rider=10.0, horse=20.0),
                    z = dict(rider=4.0, horse=4.0)
                ),
                gallop=dict(
                    x = dict(rider=10.0, horse=10.0),
                    y = dict(rider=10.0, horse=10.0),
                    z = dict(rider=4.0, horse=4.0)
                ),
                
            )
        )
    )
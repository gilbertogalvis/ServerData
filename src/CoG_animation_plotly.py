import numpy as np
import trimesh
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from CoG_repo.src.CoG_utils import load_json_file


get_vertices = lambda d, a, i: np.array([v[a][0][i] for v in d['vertices']])

class CoGAnimationPloly:
    def __init__(self, **kwargs):

        self.msize = kwargs.get( 'msize', 15 )
        self.line_width = kwargs.get( 'line_width', 10 )
        
        self.json_mesh_data = kwargs.get( 'json_mesh_data', 'docs/blender/mesh_data/rider_horse_mesh_data_tri.json' )
        self.mesh_simplify_percent = kwargs.get( 'mesh_simplify_percent', 0.95 )
        self.gait_colors = kwargs.get( 'gait_colors', dict(
            walk  = 'rgba(255,0,0,a)',
            trot  = 'rgba(0,0,255,a)',
            gallop= 'rgba(0,255,0,a)',
            stay  = 'rgba(80,80,80,a)',
        ))
        self.mesh_color = kwargs.get( 'mesh_color', 'lightgray' )
        self.mesh_alpha = kwargs.get( 'mesh_alpha', 0.1 )
        self.axis = kwargs.get( 'axis', ['x', 'y', 'z'] )
        self.win_seconds = kwargs.get( 'win_seconds', 1 )
        
        self.cog_axis = dict(
            horse = dict(
                origin=np.array((0.00, 0.00, 1.25)), 
                x=(-0.400, 1.500), 
                y=(None, None), 
                z=(0.750, 1.750)
            ),
            rider = dict(
                origin=np.array((0.50, 0.00, 2.00)), 
                x=(0.100, None), 
                y=(None, None), 
                z=(1.500, 2.500)
            ),
            color='black',
        )
        
        self.load_mesh_data()
    
    # ---------------------------------------------------------
    # load data
    
    def get_alpha(self, gait, p=0.6, m=10 ):
        n = len(gait)
        x = np.linspace(0.4, 0.9, n)
        return 1 / (1 + np.exp(-m * (x - p)))

    def load_mesh_data( self, index=1 ):
        mesh_data = load_json_file( self.json_mesh_data )
        
        y, x, z = get_vertices(mesh_data, 'x', index), get_vertices(mesh_data, 'y', index), -get_vertices(mesh_data, 'z', index)
        x -= np.min(x) + 0.75
        y -= np.mean(y)
        
        print(x.shape, y.shape, z.shape, np.array(mesh_data['caras']).shape)
        mesh = trimesh.Trimesh(
            vertices=np.array([x,y,z]).T, faces=mesh_data['caras']
        ).simplify_quadric_decimation(
            percent=self.mesh_simplify_percent
        )

        self.mesh_data = dict(
            x = np.array(mesh.vertices[:, 0]), 
            y = np.array(mesh.vertices[:, 1]),
            z = np.array(mesh.vertices[:, 2]),
            faces = np.array(mesh.faces),
        )
        print(self.mesh_data['x'].shape, self.mesh_data['y'].shape, self.mesh_data['z'].shape, self.mesh_data['faces'].shape)
        
        self.mesh_data.update(
            dict(
                min = dict(
                    x=np.min(self.mesh_data['x']),
                    y=np.min(self.mesh_data['y']),
                    z=np.min(self.mesh_data['z']),
                ),
                max = dict(
                    x=np.max(self.mesh_data['x']),
                    y=np.max(self.mesh_data['y']),
                    z=np.max(self.mesh_data['z']),
                ),
            )
        )
        
        # import json
        # with open('docs/blender/mesh_data/mesh_data.json', 'w') as f:
        #     d = dict(
        #         x = self.mesh_data['x'].tolist(),
        #         y = self.mesh_data['y'].tolist(),
        #         z = self.mesh_data['z'].tolist(),
        #         faces = self.mesh_data['faces'].tolist(),
        #         min = dict(
        #             x=self.mesh_data['min']['x'],
        #             y=self.mesh_data['min']['y'],
        #             z=self.mesh_data['min']['z'],
        #         ),
        #         max = dict(
        #             x=self.mesh_data['max']['x'],
        #             y=self.mesh_data['max']['y'],
        #             z=self.mesh_data['max']['z'],
        #         ),
        #     )
        #     json.dump(d, f, indent=4, sort_keys=True)
    
    def get_mesh(self, **kwargs):
        return go.Mesh3d(
            x=self.mesh_data['x'], y=self.mesh_data['y'], z=self.mesh_data['z'],
            i=self.mesh_data['faces'][:, 0], j=self.mesh_data['faces'][:, 1], k=self.mesh_data['faces'][:, 2],
            
            color       =kwargs.get('mesh_color', self.mesh_color),
            opacity     =kwargs.get('mesh_alpha', self.mesh_alpha),
            flatshading =False,
            lighting    =dict(
                ambient=0.8,
                diffuse=0.4,
                fresnel=0.4,
                specular=0.4,
            ),
            # lightposition=dict(x=100, y=100, z=100)  # Dirección de la luz
            name='horse_mesh',
            showlegend=False,
            hoverinfo='skip',
        )
    
    def get_cog_axis(self, **kwargs):
        origin_axes = { a:[] for a in self.axis }
        
        for o,ps in self.cog_axis.items():
            if o=='color': continue
            
            for i,a in enumerate(self.axis):
                coords = [ps['origin'].copy() for _ in range(2)]
                coords[0][i] = self.mesh_data['min'][a] if ps[a][0] is None else ps[a][0]
                coords[1][i] = self.mesh_data['max'][a] if ps[a][1] is None else ps[a][1]
                
                for ii,aa in enumerate(self.axis):
                    origin_axes[aa] += [c[ii] for c in coords] + [None]
        
        # print(origin_axes['x'], origin_axes['y'], origin_axes['z'])
        return go.Scatter3d(
            x=origin_axes['x'], y=origin_axes['y'], z=origin_axes['z'],
            
            mode  ='lines',
            line  =dict(color=self.cog_axis['color'], width=4),
            showlegend =False,
            hoverinfo  ='skip',
        )
    
    def get_template(self, **kwargs):
        mesh = self.get_mesh(**kwargs)
        cog_axis = self.get_cog_axis(**kwargs)
        
        return (
            mesh, 
            cog_axis,
            go.Scatter3d(visible=True, showlegend=False), 
        )
    
    def fig_init(self):
        self.fig = go.Figure( data=self.get_template() )
    
    def fig_layout(self, **kwargs):
        view = kwargs.get('view', [1.2, 45, 0.1])
        view[1] = np.deg2rad(view[1])
        
        self.fig.update_layout(
            margin        =dict(l=0, r=0, b=0, t=0),
            paper_bgcolor =kwargs.get('paper_bgcolor', 'black'),
            # width         =kwargs.get('w', int(1200*1.5)),
            # height        =kwargs.get('h', 1200),
            # autosize      =False,  # Desactiva el ajuste automático
            
            scene=dict(
                camera=dict(
                    eye    =dict(
                        x=view[0]*np.cos(view[1]), 
                        y=view[0]*np.sin(view[1]), 
                        z=view[2],
                    ), 
                    up     =dict(x= 0.0, y=0, z=0.2),
                    center =dict(x=-0.1, y=0, z=0.1),
                ),
                
                aspectmode='data'
            ),
        )
        
        if kwargs.get('do_menu', False):
            frame_args = lambda duration=16, t=0: {
                "frame": {"duration": duration},
                "mode": "immediate",
                "fromcurrent": True,
                "redraw": False,
                "transition" : {"duration": t},
            }
            
            sliders = [
                {
                    "pad": {"b": 10, "t": 10},
                    "len": 0.8,
                    "x": 0.1,
                    "y": 0.00,
                    "font": {"size": 10,},

                    "steps": [
                        {
                            "args": [[f.name], frame_args()],
                            # "label": str(k),
                            "label": f.name,
                            "method": "animate",
                        } 
                        for k, f in enumerate(self.fig.frames)
                    ],
                    
                    "active": 0,
                    "yanchor": "top",
                    "xanchor": "left",
                    
                    "currentvalue": {
                        "font": {"size": 10,},
                        "prefix": "Time: ",
                        "visible": True,
                        # "xanchor": "center"
                    },
                }
            ]
            
            self.fig.update_layout(
                updatemenus=[
                    {
                        "buttons": [
                            {
                                "args": [None, frame_args()],
                                "label": "▶️ Play",
                                "method": "animate",
                            },
                            {
                                "args": [[None], frame_args()],
                                "label": "⏹️ Stop",
                                "method": "animate",
                            }
                        ],

                        "direction": "left",
                        "pad": {"r": 0, "t": 25},
                        "type": "buttons",
                        "x": 0.53,
                        "y": 0,
                    }
                ],
                
                sliders=sliders
            )
    
    def do_frame(self, data, **kwargs):
        n_samples = len(data['rider_cog'])
        yaw, ts = data['yaw'], data['ts']
        rider_cog, horse_cog, gait = data['rider_cog'], data['horse_cog'], data['gait']
        
        alpha = self.get_alpha( gait, p=0.6, m=10 )
        color = [ self.gait_colors[g].replace( 'a)', '%f)' %(alpha[i]) ) for i,g in enumerate(gait) ]
        size  = [0]*(n_samples-1) + [kwargs.get('msize', self.msize)]
        
        scatter = go.Scatter3d(
            x=list(rider_cog[:, 0]) + [None] + list(horse_cog[:, 0]),
            y=list(rider_cog[:, 1]) + [None] + list(horse_cog[:, 1]),
            z=list(rider_cog[:, 2]) + [None] + list(horse_cog[:, 2]),
            
            marker =dict(
                size=size + [0] + size, 
            ),
            
            line   =dict(
                color= color+['rgba(0,0,0,0)']+color,
                width= kwargs.get('line_width', self.line_width),
            ),
        )
        
        return go.Frame(
            data=[scatter],
            traces=[2],
            name=ts,
        )
        
    def fig_add_frames(self, data, **kwargs):
        win_seconds = kwargs.get('win_seconds', self.win_seconds)
        win_samples = int( win_seconds * data['fs'] )
        indices = np.arange( -(win_samples-1), 1 ).astype(np.intp)
        n_frames = len(data['ts'])
        
        
        frames = []
        for i in range(n_frames):
            current_indices = indices[indices>=0]
            current_data = dict(
                rider_cog=data['rider_cog'][current_indices] + self.cog_axis['rider']['origin'], 
                horse_cog=data['horse_cog'][current_indices] + self.cog_axis['horse']['origin'],
                gait=data['gait'][current_indices],
                yaw=data['yaw'][i],
                ts=data['ts'][i][:-3],
            )
            
            frames.append( self.do_frame(data=current_data, **kwargs) )
            indices += 1
        
        self.fig.update(frames=frames)
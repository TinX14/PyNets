#!/bin/env python -W ignore::DeprecationWarning
import sys
from nipype.interfaces.base import isdefined,Undefined
######################
if len(sys.argv) > 1:
    try:
        input_file=sys.argv[1]
    except:
        print("Error: You must include a file path, in quotes, to either a standard space functional image in .nii or .nii.gz format or a path to a time-series text/csv file")
        sys.exit()
    try:
        ID=sys.argv[2]
    except:
        print("Error: You must include a subject ID as your second entry on the command line")
        sys.exit()
    if '.nii' in input_file:
        try:
            atlas_select=sys.argv[3]
        except:
            print("Error: You have specified the path to an image file. You must also include an atlas name as the third argument to your PyNets.py call")
            sys.exit()
    else:
        atlas_select=Undefined
    if '.nii' in input_file:
        try:
            TR=sys.argv[4]
        except:
            print("Error: You have specified the path to an image file. You must also include a TR value as the fourth argument to your PyNets.py call")
            sys.exit()
    else:
        #TR=Undefined
        TR=''
        #atlas_select=Undefined
        atlas_select=''
else:
    print("Missing command-line inputs!\n\nYou musty include: \n1) Either a path to a functional image in standard space and .nii or .nii.gz format OR an input time-series text/csv file \n2) A subject ID (numerical) for those files\n\n\n*If a functional image file is used, you must also select: \n3) An atlas from the list below \n4) A TR value\n\n\n'abide_pcp'\n'adhd'\n'atlas_aal'\n'atlas_basc_multiscale_2015'\n'atlas_craddock_2012'\n'atlas_destrieux_2009'\n'atlas_harvard_oxford'\n'atlas_msdl'\n'atlas_smith_2009'\n'atlas_yeo_2011'\n'cobre'\n'coords_dosenbach_2010'\n'coords_power_2011'\n'haxby'\n'haxby_simple'\n'icbm152_2009'\n'icbm152_brain_gm_mask'\n'localizer_button_task'\n'localizer_calculation_task'\n'localizer_contrasts'\n'megatrawls_netmats'\n'mixed_gambles'\n'miyawaki2008'\n'nyu_rest'\n'oasis_vbm'\n")
    sys.exit()

######################

import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
import nilearn
import numpy as np
import bct
import os
from numpy import genfromtxt
from sklearn.covariance import GraphLassoCV
from matplotlib import pyplot as plt
from nipype import Node, Workflow
from nipype.pipeline import engine as pe
from nipype.interfaces import utility as niu
from nipype.interfaces import io as nio
from nilearn import datasets
from nilearn.input_data import NiftiLabelsMasker
from nilearn.connectome import ConnectivityMeasure
from nilearn import input_data
from nilearn import plotting
import networkx as nx
from nipype.interfaces.base import BaseInterface, BaseInterfaceInputSpec, TraitedSpec, File, traits, Str

import_list=["import nilearn", "import numpy as np", "import os", "import bct", "from numpy import genfromtxt", "from matplotlib import pyplot as plt", "from nipype import Node, Workflow", "from nipype import Node, Workflow", "from nipype.pipeline import engine as pe", "from nipype.interfaces import utility as niu", "from nipype.interfaces import io as nio", "from nilearn import plotting", "from nilearn import datasets", "from nilearn.input_data import NiftiLabelsMasker", "from nilearn.connectome import ConnectivityMeasure", "from nilearn import input_data", "from nilearn import plotting", "import networkx as nx", "import nibabel as nib"]

print("\n\n\n")
print ("INPUT FILE: " + input_file)
print("\n")
print ("SUBJECT ID: " + ID)
if '.nii' in input_file:
    print("\n")
    print ("ATLAS: " + atlas_select)
    print("\n")
    print ("TR: " + TR)
print("\n\n\n")
dir_path = os.path.dirname(os.path.realpath(input_file))

##Import ts and estimate cov
def import_mat_func(input_file, ID, atlas_select, TR):
    if '.nii' in input_file:
        from nilearn import datasets
        func_file=input_file
        dir_path = os.path.dirname(os.path.realpath(func_file))
        atlas = getattr(datasets, 'fetch_%s' % atlas_select)()
        atlas_name = atlas['description'].splitlines()[0]
        print("\n")
        print(atlas_name + ' comes with {0}.'.format(atlas.keys()))
        print("\n")
        coords = np.vstack((atlas.rois['x'], atlas.rois['y'], atlas.rois['z'])).T
        print("\n")
        print('Stacked atlas coordinates in array of shape {0}.'.format(coords.shape))
        print("\n")
        spheres_masker = input_data.NiftiSpheresMasker(
            seeds=coords, smoothing_fwhm=6, radius=5.,
            detrend=True, standardize=True, low_pass=0.1, high_pass=0.01, t_r=float(TR))
        time_series = spheres_masker.fit_transform(func_file)
        correlation_measure = ConnectivityMeasure(kind='correlation')
        correlation_matrix = correlation_measure.fit_transform([time_series])[0]
        print("\n")
        print('Time series has {0} samples'.format(time_series.shape[0]))
        print("\n")
        plt.imshow(correlation_matrix, vmin=-1., vmax=1., cmap='RdBu_r', interpolation='nearest')
        plt.colorbar()
        plt.title(atlas_name + ' correlation matrix')
        out_path_fig=dir_path + '/' + ID + '_' + atlas_name + '_adj_mat_cov.png'
        plt.savefig(out_path_fig)
        plt.close()
        # Tweak edge_threshold to keep only the strongest connections.
        atlast_graph_title = atlas_name + ' correlation graph'
        plotting.plot_connectome(correlation_matrix, coords, title=atlast_graph_title, edge_threshold='99.5%', node_size=20, colorbar=True)
        out_path_fig=dir_path + '/' + ID + '_' + atlas_name + '_connectome_viz.png'
        plt.savefig(out_path_fig)
        plt.close()
        time_series_path = dir_path + '/' + ID + '_ts.txt'
        np.savetxt(time_series_path, time_series, delimiter='\t')
        mx = genfromtxt(time_series_path, delimiter='')
    else:
        DR_st_1=input_file
        dir_path = os.path.dirname(os.path.realpath(DR_st_1))
        mx = genfromtxt(DR_st_1, delimiter='')
    from sklearn.covariance import GraphLassoCV
    estimator = GraphLassoCV()
    est = estimator.fit(mx.T)
    est_path1 = dir_path + '/' + ID + '_est_cov.txt'
    est_path2 = dir_path + '/' + ID + '_est_sps_inv_cov.txt'
    np.savetxt(est_path1, estimator.covariance_, delimiter='\t')
    np.savetxt(est_path2, estimator.precision_, delimiter='\t')
    return(mx, est_path1, est_path2)

##Display the covariance
def cov_plt_func(mx, est_path1, ID):
    rois_num=mx.shape[0]
    ts_num=mx.shape[1]
    dir_path = os.path.dirname(os.path.realpath(est_path1))
    est_cov = genfromtxt(est_path1)
    plt.figure(figsize=(10, 10))
    ##The covariance can be found at estimator.covariance_
    plt.imshow(est_cov, interpolation="nearest", vmax=1, vmin=-1, cmap=plt.cm.RdBu_r)
    ##And display the labels
    x_ticks = plt.xticks(range(rois_num), rotation=90)
    y_ticks = plt.yticks(range(rois_num))
    plt.title('Covariance')
    A=np.matrix(est_cov)
    G=nx.from_numpy_matrix(A)
    G = nx.write_graphml(G, dir_path + '/' + ID + '.graphml')
    out_path=dir_path + '/' + ID + '_adj_mat_cov.png'
    plt.savefig(out_path)
    plt.close()
    return(est_path1)

def sps_inv_cov_plt_func(mx, est_path2, ID):
    rois_num=mx.shape[0]
    ts_num=mx.shape[1]
    dir_path = os.path.dirname(os.path.realpath(est_path2))
    est_sps_inv_cov = genfromtxt(est_path2)
    plt.figure(figsize=(10, 10))
    ##The covariance can be found at estimator.precision_
    plt.imshow(-est_sps_inv_cov, interpolation="nearest",
               vmax=1, vmin=-1, cmap=plt.cm.RdBu_r)
    ##And display the labels
    x_ticks = plt.xticks(range(rois_num), rotation=90)
    y_ticks = plt.yticks(range(rois_num))
    plt.title('Sparse inverse covariance')
    A=np.matrix(est_sps_inv_cov)
    G=nx.from_numpy_matrix(A)
    G = nx.write_graphml(G, dir_path + '/' + ID + '.graphml')
    out_path=dir_path + '/' + ID + '_adj_mat_sps_inv_cov.png'
    plt.savefig(out_path)
    plt.close()
    return(est_path2)

def extractnetstats(est_path, ID, out_file=None):
    in_mat = np.array(genfromtxt(est_path))
    dir_path = os.path.dirname(os.path.realpath(est_path))
    efficiency_bin = float(bct.efficiency_bin(in_mat))
    efficiency_wei = float(bct.efficiency_wei(in_mat))
    modularity_finetune_dir = float(bct.modularity_finetune_dir(in_mat)[1])
    modularity_finetune_und_sign = float(bct.modularity_finetune_und_sign(in_mat)[1])
    modularity_und = float(bct.modularity_und(in_mat)[1])
    modularity_louvain_dir = float(bct.modularity_louvain_dir(in_mat)[1])
    modularity_louvain_und = float(bct.modularity_louvain_und(in_mat)[1])
    modularity_louvain_und_sign = float(bct.modularity_louvain_und_sign(in_mat)[1])
    modularity_probtune_und_sign = float(bct.modularity_probtune_und_sign(in_mat)[1])
    transitivity_bu = float(bct.transitivity_bu(in_mat))
    transitivity_wd = float(bct.transitivity_wd(in_mat))
    assortativity_bin = float(bct.assortativity_bin(in_mat))
    assortativity_wei = float(bct.assortativity_wei(in_mat))
    density_dir = float(bct.density_dir(in_mat)[0])
    charpath = float(bct.charpath(in_mat)[4])
    if 'inv' in est_path:
      out_path = dir_path + '/' + ID + '_net_global_scalars_inv_sps_cov.csv'
    else:
      out_path = dir_path + '/' + ID + '_net_global_scalars_cov.csv'
    np.savetxt(out_path, [efficiency_bin, efficiency_wei, modularity_finetune_dir, modularity_finetune_und_sign, modularity_und, modularity_louvain_dir, modularity_louvain_und, modularity_louvain_und_sign, modularity_probtune_und_sign, transitivity_bu, transitivity_wd, assortativity_bin, assortativity_wei, density_dir, charpath])
    return out_path

class ExtractNetStatsInputSpec(BaseInterfaceInputSpec):
    est_path = File(exists=True, mandatory=True, desc="")
    sub_id = Str(mandatory=True)

class ExtractNetStatsOutputSpec(TraitedSpec):
    out_file = File()

class ExtractNetStats(BaseInterface):
    input_spec = ExtractNetStatsInputSpec
    output_spec = ExtractNetStatsOutputSpec

    def _run_interface(self, runtime):
        out = extractnetstats(
            self.inputs.est_path,
            self.inputs.sub_id,
        )
        setattr(self, '_outpath', out)
        return runtime

    def _list_outputs(self):
        import os.path as op
        return {'out_file': op.abspath(getattr(self, '_outpath'))}

##save global scalar files to pandas dataframes
def export_to_pandas(csv_loc, ID, out_file=None):
    import pandas as pd
    df = pd.read_csv(csv_loc, delimiter='\t', header=None).fillna('')
    df = df.T
    df = df.rename(columns={0:"efficiency_bin", 1:"efficiency_wei", 2:"modularity_finetune_dir", 3:"modularity_finetune_und_sign", 4:"modularity_und", 5:"modularity_louvain_dir", 6:"modularity_louvain_und", 7:"modularity_louvain_und_sign", 8:"modularity_probtune_und_sign", 9:"transitivity_bu", 10:"transitivity_wd", 11:"assortativity_bin", 12:"assortativity_wei",
    13:"density_dir", 14:"charpath"})
    df['id'] = range(1, len(df) + 1)
    if 'id' in df.columns:
        cols = df.columns.tolist()
        ix = cols.index('id')
        cols_ID = cols[ix:ix+1]+cols[:ix]+cols[ix+1:]
        df = df[cols_ID]
    df['id'].values[0] = ID
    out_file = csv_loc.replace('.', '')[:-3] + '_' + ID
    df.to_pickle(out_file)
    return(out_file)

class Export2PandasInputSpec(BaseInterfaceInputSpec):
    in_csv = File(exists=True, mandatory=True, desc="")
    sub_id = Str(mandatory=True)
    out_file = File('output_export2pandas.csv', usedefault=True)

class Export2PandasOutputSpec(TraitedSpec):
    out_file = File()

class Export2Pandas(BaseInterface):
    input_spec = Export2PandasInputSpec
    output_spec = Export2PandasOutputSpec

    def _run_interface(self, runtime):
        export_to_pandas(
            self.inputs.in_csv,
            self.inputs.sub_id,
            out_file=self.inputs.out_file
        )
        return runtime

    def _list_outputs(self):
        import os.path as op
        return {'out_file': op.abspath(self.inputs.out_file)}

##Create input/output nodes
inputnode = pe.Node(niu.IdentityInterface(fields=['in_file', 'ID', 'atlas_select', 'TR']),
                    name='inputnode')
inputnode.inputs.in_file = input_file
inputnode.inputs.ID = ID
inputnode.inputs.atlas_select = atlas_select
inputnode.inputs.TR = TR

##Create function nodes
imp_est = pe.Node(niu.Function(input_names = ['input_file', 'ID', 'atlas_select', 'TR'], output_names = ['mx','est_path1', 'est_path2'], function=import_mat_func, imports=import_list), name = "imp_est")
cov_plt = pe.Node(niu.Function(input_names = ['mx', 'est_path1', 'ID'], output_names = ['est_path1'], function=cov_plt_func, imports=import_list), name = "cov_plt")
sps_inv_cov_plt = pe.Node(niu.Function(input_names=['mx', 'est_path2', 'ID'], output_names = ['est_path2'], function=sps_inv_cov_plt_func, imports=import_list), name = "sps_inv_cov_plt")
net_glob_scalars_cov = pe.Node(ExtractNetStats(), name = "ExtractNetStats1")
net_global_scalars_inv_sps_cov = pe.Node(ExtractNetStats(), name = "ExtractNetStats2")
export_to_pandas1 = pe.Node(Export2Pandas(), name = "export_to_pandas1")
export_to_pandas2 = pe.Node(Export2Pandas(), name = "export_to_pandas2")

##Create PyNets workflow
wf = pe.Workflow(name='PyNets_WORKFLOW')
wf.base_directory='/tmp/nipype'

##Create data sink
#datasink = pe.Node(nio.DataSink(), name='sinker')
#datasink.inputs.base_directory = dir_path + '/DataSink'

##Connect nodes of workflow
wf.connect([
    (inputnode, imp_est, [('in_file', 'input_file'),
                          ('ID', 'ID'),
                          ('atlas_select', 'atlas_select'),
                          ('TR', 'TR')]),
    (inputnode, cov_plt, [('ID', 'ID')]),
    (imp_est, cov_plt, [('mx', 'mx'),
                        ('est_path1', 'est_path1')]),
    (imp_est, sps_inv_cov_plt, [('mx', 'mx'),
                                ('est_path2', 'est_path2')]),
    (inputnode, sps_inv_cov_plt, [('ID', 'ID')]),
    (imp_est, net_glob_scalars_cov, [('est_path1', 'est_path')]),
    (inputnode, net_glob_scalars_cov, [('ID', 'sub_id')]),
    (imp_est, net_global_scalars_inv_sps_cov, [('est_path2', 'est_path')]),
    (inputnode, net_global_scalars_inv_sps_cov, [('ID', 'sub_id')]),
#    (net_glob_scalars_cov, datasink, [('est_path1', 'csv_loc')]),
#    (net_global_scalars_inv_sps_cov, datasink, [('est_path2', 'csv_loc')]),
    (inputnode, export_to_pandas1, [('ID', 'sub_id')]),
    (net_glob_scalars_cov, export_to_pandas1, [('out_file', 'in_csv')]),
    (inputnode, export_to_pandas2, [('ID', 'sub_id')]),
    (net_global_scalars_inv_sps_cov, export_to_pandas2, [('out_file', 'in_csv')]),
#    (export_to_pandas1, datasink, [('out_file', 'pandas_df1')]),
#    (export_to_pandas2, datasink, [('out_file', 'pandas_df2')]),
])

wf.write_graph()
#wf.run(plugin='SLURM')
#wf.run(plugin='MultiProc')
wf.run()

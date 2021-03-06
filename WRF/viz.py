#
# WRF visualization helper module
#
# written by Eliot Quon (eliot.quon@nrel.gov)
#
from __future__ import print_function
import os
from glob import glob
from datetime import datetime

import xarray
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib import cm

from ipywidgets import interactive #interact, interactive, fixed, interact_manual
import ipywidgets as widgets
from IPython.display import display

from datatools.SOWFA.constant.forcingTable import ForcingTable

g = 9.81
#contour_colormap = 'bwr' # closest to what's available in ncview
contour_colormap = 'RdBu_r' # more soothing blues and reds
series_colormap = 'viridis'

class Visualization2D(object):

    def __init__(self,*args,**kwargs):
        """Create visualization object
        
        Keyword arguments
        =================
        ds : float, optional
            Grid spacing (assumed uniform)
        parse_datetime : str, optional
            Specified strftime string to parse filenames into datetimes
        """
        self.ds = kwargs.get('ds',1.0)
        parse_datetime = kwargs.get('parse_datetime',None)

        plane = kwargs.get('plane','z') # 2D plane normal direction
        if not plane=='z':
            raise NotImplementedError('Only z planes for now') 

        tdim = kwargs.get('tdim','time') # time / file aggregation dimension ("aggdim")
        xdim = kwargs.get('xdim','west_east') # unstaggered by default
        ydim = kwargs.get('ydim','south_north') # unstaggered by default
        zdim = kwargs.get('zdim','bottom_top') # unstaggered by default

        """Load a series of netcdf files provided by args"""
        if len(args) > 0:
            inputfiles = []
            for fpath in args:
                if os.path.isfile(fpath):
                    inputfiles.append(fpath)
                else:
                    inputfiles += glob(fpath)
        else:
            inputfiles = os.listdir('.')
        filelist = []
        for fpath in inputfiles:
            if not os.path.isfile(fpath):
                continue
            try:
                xarray.open_dataset(fpath)
            except (IOError,OSError):
                # NetCDF: Unknown file format
                continue
            else:
                filelist.append(fpath)
        filelist.sort()
        self.filelist = filelist
        self.data = xarray.open_mfdataset(filelist, concat_dim=tdim)

        """Set up dimensions"""
        self.plane = plane
        assert(plane in ['x','y','z'])
        self.Ntimes = self.data.dims[tdim]
        self.Nx = self.data.dims[xdim]
        self.Ny = self.data.dims[ydim]
        self.Nz = self.data.dims[zdim]
        if plane == 'x':
            self.N = self.Nx
        elif plane == 'y':
            self.N = self.Ny
        elif plane == 'z':
            self.N = self.Nz

        if parse_datetime is not None:
            # parse_datetime is the datetime format
            self.times = np.array([datetime.strptime(os.path.split(fname)[-1], parse_datetime)
                                   for fname in self.filelist])
        else:
            self.times = np.arange(self.Ntimes)

        """Set up field variables"""
        # unstaggered
        self.T = self.data.variables['T'][:] + 300.0
        # staggered in x
        U = self.data.variables['U'][:]
        self.U = 0.5*(U[:,:,:,:-1] + U[:,:,:,1:])
        # staggered in y
        V = self.data.variables['V'][:]
        self.V = 0.5*(V[:,:,:-1,:] + V[:,:,1:,:])
        # staggered in z
        W = self.data.variables['W'][:]
        PH = self.data.variables['PH'][:]
        PHB = self.data.variables['PHB'][:]
        self.W = 0.5*(W[:,:-1,:,:] + W[:,1:,:,:])
        # calculate z = (ph + phb)/g
        self.z = 0.5*( PH[:,:-1,:,:] +  PH[:,1:,:,:] +
                      PHB[:,:-1,:,:] + PHB[:,1:,:,:] ) / g
        # other variables
        #self.Umag = np.sqrt(self.U**2 + self.V**2 + self.W**2) # can cause a memory error
        self.z_est = np.mean(self.z.values, axis=(2,3))
        
    def __repr__(self):
        s = str(self.Ntimes) + ' times read:\n'
        for fpath in self.filelist[:3]:
            s += '  ' + os.path.split(fpath)[-1] + '\n'
        if len(self.filelist) > 5:
            s += '  ...\n'
        for fpath in self.filelist[-2:]:
            s += '  ' + os.path.split(fpath)[-1] + '\n'
        s += 'Dimensions: ({:d}, {:d}, {:d})'.format(self.Nx,
                                                     self.Ny,
                                                     self.Nz)
        return s

    def interactive(self):
        """Create an interactive plot"""
        xlim_slider = widgets.IntRangeSlider(min=0, max=self.Nx-1, value=[0,self.Nx-1])
        ylim_slider = widgets.IntRangeSlider(min=0, max=self.Ny-1, value=[0,self.Ny-1])
        self.iplot = interactive(self.plot,
                                 field=['U','V','W','T'],
                                 time=(0, self.Ntimes-1),
                                 index=(0, self.N-1),
                                 xlim=xlim_slider,
                                 ylim=ylim_slider)
        display(self.iplot)

    def plot(self,field='U',time=0,index=0,xlim=(0,-1),ylim=(0,-1)):
        """Callback for Visualization2D.interactive() to make contour plot"""
        length_units = 'm'
        # TODO: Only z-planes handled for now
        if self.plane == 'z':
            assert((index >= 0) and (index < self.Nz))
            plt.figure(1,figsize=(10,6))
            U = getattr(self,field)
            U = U[time,:,:,:]
            # set image left, right, bottom, top
            extent = np.array((0.0, (self.Nx-1)*self.ds,
                              (self.Ny-1)*self.ds, 0.0)
                             ) # note top/bottom flipped when using imshow
            if np.max(extent) > 10000:
                rescale = True
                extent /= 1000.
                length_units = 'km'
            # use imshow (fastest)
            cont = plt.imshow(U[index,:,:],cmap=contour_colormap,extent=extent)
            # format plot
            plt.xlabel('x [{:s}]'.format(length_units))
            plt.ylabel('y [{:s}]'.format(length_units))
            plt.gca().invert_yaxis()
            plt.title('{:s}, z ~= {:.1f} m'.format(str(self.times[time]),
                                                   self.z_est[time,index]))
            # add bounding box for averaging region
            if (xlim[0] > 0) or (xlim[1] < self.Nx-1) \
                    or (ylim[0] > 0) or (ylim[1] < self.Ny-1):
                xr = np.array(xlim) * self.ds
                yr = np.array(ylim) * self.ds
                if rescale:
                    xr /= 1000.
                    yr /= 1000.
                rect = Rectangle((xr[0],yr[0]), np.diff(xr), np.diff(yr),
                                 fill=False, color='k', linestyle='--')
                plt.gca().add_patch(rect)
            # add colorbar
            cbar = plt.colorbar(cont)
            cbar.set_label(field)
        else:
            print(self.plane,'not supported')
        plt.show()

    def _print_mean_info(self):
        xr = self.iplot.kwargs['xlim']
        yr = self.iplot.kwargs['ylim']
        print('mean over i in [{:d} {:d}], j in [{:d} {:d}]'.format(xr[0],xr[1],
                                                                    yr[0],yr[1]))
        print('  x:{}, y:{}'.format(self.ds*np.array(xr),
                                    self.ds*np.array(yr)))
        print('  area is {:.1f} by {:.1f} m^2'.format(self.ds*np.diff(xr)[0],
                                                      self.ds*np.diff(yr)[0]))

    def plot_mean_profile(self,itime=None,field=None):
        """Plot the mean profile averaged over the xlim and ylim 
        specified by the interactive widgets.
        """
        params = self.iplot.kwargs
        if itime is None:
            itime = params['time']
        xr = params['xlim']
        yr = params['ylim']
        self._print_mean_info()
        z = self.z
        if field is None:
            field = params['field']
        U = getattr(self,field)
        zmean = np.mean(z[itime,:,yr[0]:yr[1]+1,xr[0]:xr[1]+1], axis=(1,2))
        Umean = np.mean(U[itime,:,yr[0]:yr[1]+1,xr[0]:xr[1]+1], axis=(1,2))
        plt.figure(2, figsize=(4,6))
        plt.plot(Umean, zmean)
        plt.xlabel(field)
        plt.ylabel('z [m]')
        plt.title('itime={:d}'.format(itime))

    def plot_mean_profiles_over_time(self,field=None):
        """Plot mean profiles for all times loaded. Averaging is
        performed over xlim and ylim specified by the interactive
        widgets.
        """
        params = self.iplot.kwargs
        xr = params['xlim']
        yr = params['ylim']
        self._print_mean_info()
        z = self.z
        if field is None:
            field = params['field']
        U = getattr(self,field)
        print('averaging {:s} over {:d} times, could take a minute...'.format(field,self.Ntimes))
        zmean = np.mean(z[:,:,yr[0]:yr[1]+1,xr[0]:xr[1]+1], axis=(2,3))
        Umean = np.mean(U[:,:,yr[0]:yr[1]+1,xr[0]:xr[1]+1], axis=(2,3))
        plt.figure(3, figsize=(4,6))
        colfun = cm.get_cmap(series_colormap)
        for itime in range(self.Ntimes):
            color = colfun(float(itime)/(self.Ntimes-1))
            label = ''
            if (itime == 0) or (itime == self.Ntimes-1):
                #label = 'time'+str(itime)
                label = self.times[itime]
            plt.plot(Umean[itime,:], zmean[itime,:], color=color, label=label)
        plt.xlabel(field)
        plt.ylabel('z [m]')
        plt.legend(loc='best')

    def timeheight_plot_mean(self,field=None):
        """Plot mean profiles for all times loaded in the time-height
        contour format. Averaging is performed over xlim and ylim
        specified by the interactive widgets.
        """
        params = self.iplot.kwargs
        xr = params['xlim']
        yr = params['ylim']
        self._print_mean_info()
        z = self.z
        if field is None:
            field = params['field']
        U = getattr(self,field)
        print('averaging {:s} over {:d} times, could take a minute...'.format(field,self.Ntimes))
        zmean = np.mean(z[:,:,yr[0]:yr[1]+1,xr[0]:xr[1]+1], axis=(2,3))
        Umean = np.mean(U[:,:,yr[0]:yr[1]+1,xr[0]:xr[1]+1], axis=(2,3))
        plt.figure(4, figsize=(10,4))
        alltimes = np.tile(self.times,[self.Nz,1]).T
        cont = plt.contourf(alltimes, zmean, Umean, cmap=contour_colormap)
        cbar = plt.colorbar(cont)
        cbar.set_label(field)
        plt.ylabel('z [m]')

    def get_forcing_table(self):
        params = self.iplot.kwargs
        xr = params['xlim']
        yr = params['ylim']
        self._print_mean_info()
        print('averaging over {:d} times, could take a minute...'.format(self.Ntimes))
        zmean = np.mean(self.z[:,:,yr[0]:yr[1]+1,xr[0]:xr[1]+1], axis=(2,3))
        Umean = np.mean(self.U[:,:,yr[0]:yr[1]+1,xr[0]:xr[1]+1], axis=(2,3))
        Vmean = np.mean(self.V[:,:,yr[0]:yr[1]+1,xr[0]:xr[1]+1], axis=(2,3))
        Wmean = np.mean(self.W[:,:,yr[0]:yr[1]+1,xr[0]:xr[1]+1], axis=(2,3))
        Tmean = np.mean(self.T[:,:,yr[0]:yr[1]+1,xr[0]:xr[1]+1], axis=(2,3))
        return ForcingTable(heights=zmean, times=self.times,
                            U=Umean, V=Vmean, W=Wmean, T=Tmean)

    def save_forcing_table(self,z,dpath='.',name='forcingTable'):
        """Save forcingTable with specified fname at specified heights z"""
        tab = self.get_forcing_table()
        tab.regularize_heights(z)
        tab.to_csv(os.path.join(dpath,name+'.csv'))
        tab.write(os.path.join(dpath,name))
        return tab

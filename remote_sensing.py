"""
Data readers for remote sensing devices
=======================================
Written by Eliot Quon (eliot.quon@nrel.gov)

This is a collection of readers to be used with the NWTC datatools.wfip2
module for processing WFIP2 data downloaded from the A2e Data Archive
and Portal (DAP). No effort is made to standardize the names of the 
dataframe columns and the original data headers are retained wherever
possible.

"""
import numpy as np
import pandas as pd

import codecs # for utf-8 handling


#
# Lidar data readers
#

def windcube_v1(fname,
                return_header=False,
                default_columns=None,
                default_altitudes=None,
                ):
    """WindCube v1
    Users: CU Boulder, ...

    The default columns and altitudes are used when there is no header
    in the file. Can optionally return a dictionary of lidar operating
    parameters parsed from the header.
    """
    scan_info = dict()        

    # gives "UnicodeDecodeError: 'utf-8' codec can't decode byte ... in
    #   position ...: invalid start byte" error
    #with open(fname,'r') as f: 

    with open(fname,'r',encoding='utf-8',errors='ignore') as f:
        firstline = f.readline()
        if '=' in firstline:
            # we have a header
            Nheader = int(firstline.split('=')[-1])
            for _ in range(Nheader):
                line = f.readline()
                if '=' in line:
                    param_value = line.strip().split('=')
                    try:
                        ival = int(param_value[1])
                        scan_info[param_value[0]] = ival # integer
                    except ValueError: 
                        try:
                            fval = float(param_value[1]) 
                            scan_info[param_value[0]] = fval # float
                        except ValueError:
                            scan_info[param_value[0]] = param_value[1] # string
            # assume first column is "Date" which actuatlly corresponds to two
            #   separate date and time columns
            columns = ['date','time'] + f.readline().split()[1:]
            altitudes = np.array([ float(h)
                    for h in scan_info['Altitudes(m)'].strip().split('\t') ])
        else:
            # some files have no header, let's hope for the best...
            f.seek(0)
            columns = default_columns
            altitudes = default_altitudes
            
        df = pd.read_table(f,
                           delim_whitespace=True,
                           names=columns,
                           parse_dates=[['date', 'time']],
                           dayfirst=True)
        
    # unpivot the columns
    um_vars = [ 'um'+str(i) for i in range(1,len(altitudes)+1) ]
    vm_vars = [ 'vm'+str(i) for i in range(1,len(altitudes)+1) ]
    um = pd.melt(df, id_vars=['date_time'], var_name='um_var', value_name='um', value_vars=um_vars)
    vm = pd.melt(df, id_vars=['date_time'], var_name='vm_var', value_name='vm', value_vars=vm_vars)
    um['height'] = um['um_var'].map(dict(zip(um_vars, altitudes)))
    vm['height'] = vm['vm_var'].map(dict(zip(vm_vars, altitudes)))
    newdf = pd.merge(um, vm, on=['date_time','height'])
    
    # calculate wind speed and direction
    newdf['speed'] = np.sqrt(newdf['um']**2 + newdf['vm']**2)
    newdf['direction'] = 270.0 - 180.0/np.pi*np.arctan2(newdf['vm'],newdf['um'])
    newdf.loc[newdf['direction'] > 360.0,'direction'] -= 360.0
    
    # return calculated columns only
    newdf = newdf[['date_time','height','speed','direction']]    
    if return_header:
        return newdf, scan_info
    else:
        return newdf


#
# Radar data readers
#

def read_winds_data_block(f):
    """Dependency for wind_profiler radar"""
    assert(f.readline().strip() == '') # Line 1
    f.readline() # Line 2: station name
    assert(f.readline().split()[0] == 'WINDS') # Line 3: WINDS, version
    f.readline() # Line 4: lat (N), long (W), elevation (m)
    Y,m,d,H,M,S,_ = f.readline().split() # Line 5: date
    date_time = pd.to_datetime('20{}{}{} {}{}{}'.format(Y,m,d,H,M,S))
    f.readline() # Line 6: consensus averaging time
    f.readline() # Line 7: beam info
    f.readline() # Line 8: beam info
    f.readline() # Line 9: beam info
    f.readline() # Line 10: beam info
    header = f.readline().split()
    block = []
    line = f.readline()
    while not line.strip()=='$' and not line=='':
        block.append(line.split())
        line = f.readline()
    df = pd.DataFrame(data=block,columns=header,dtype=float)
    df['date_time'] = date_time
    return df

def ESRL_wind_profiler(fname,
                       height_conversion_to_m=1000.0,
                       bad_value=999999):
    """Wind Profiler radar with RASS
    Users: Earth Sciences Research Laboratory (ESRL)

    Assumed data format for consensus data format rev 5.1 based on
    provided reference for rev 4.1 from:
    https://a2e.energy.gov/data/wfip2/attach/915mhz-cns-winds-data-format.txt
    """
    dataframes = []
    with open(fname,'r') as f:
        # read 2 blocks per file (i.e., per time)
        dataframes.append(read_winds_data_block(f))
        dataframes.append(read_winds_data_block(f))
    df = pd.concat(dataframes)
    df['HT'] = df['HT']*height_conversion_to_m
    if bad_value is not None:
        try:
            for val in bad_value:
                df.loc[df['SPD']==val,'SPD'] = np.nan # flag bad values
                df.loc[df['DIR']==val,'DIR'] = np.nan # flag bad values
        except TypeError:
            df.loc[df['SPD']==bad_value,'SPD'] = np.nan # flag bad values
            df.loc[df['DIR']==bad_value,'DIR'] = np.nan # flag bad values
    return df

#
# Sodar data readers
#

# PCSodar data block format description: https://a2e.energy.gov/data/wfip2/attach/variables-in-datafile.pdf
PCSodar_header = [
        'height_m','windspeed_ms','winddirection_deg','reliability',
        'w_speed_ms','w_reliability','w_count','w_stdev_ms','w_amplitude','w_noise','w_SNR','w_valid_count',
        'v_speed_ms','v_reliability','v_count','v_stdev_ms','v_amplitude','v_noise','v_SNR','v_valid_count',
        'u_speed_ms','u_reliability','u_count','u_stdev_ms','u_amplitude','u_noise','u_SNR','u_valid_count',
        ]

def ARL_wind_profiler(fname,
                      bad_speed_value=-99.9,
                      bad_direction_value=999):
    """ARL Wind Profiler
    Users: Air Resources Laboratory (ARL), ...
    
    Read each block within a file (in PCSodar format) as a separate
    dataframe, and then return a concatenated dataframe
    """
    dataframes = []
    Nh = len(range_gates)
    with open(fname,'r') as f:
        firstline = f.readline()
        while not firstline=='':
            _,year,month,day,time,_ = firstline.replace('"','').split(',')
            date_time = pd.to_datetime('{}{}{} {}'.format(year,month,day,time[:5])) # time format is "HH:MM"
            f.readline() # ignore sodar operating parameters
            block = []
            for _ in range(Nh):
                block.append(f.readline().strip().split(','))
            df = pd.DataFrame(data=block,columns=header,dtype=float)
            assert(np.all(df['height_m'].values==range_gates)) # make sure we're always reading the number of rows we think we are
            df['date_time'] = date_time
            df.loc[df['windspeed_ms']==bad_speed_value,'windspeed_ms'] = np.nan # flag bad values
            df.loc[df['winddirection_deg']==bad_direction_value,'winddirection_deg'] = np.nan # flag bad values
            dataframes.append(df)
            firstline = f.readline()
    return pd.concat(dataframes)


def scintec_profiler(fname,
                     bad_speed_value=99.99,
                     bad_direction_value=999.9):
    """Scintec MFAS Flat Array Sodar
    
    Reads files in the APRun file format:
    https://a2e.energy.gov/data/wfip2/attach/sodar-aprun-software-manual-1-27.pdf
    """
    with open(fname,'r') as f:
        f.readline() # FORMAT-1
        dateline = f.readline() # YYYY-MM-DD HH:MM:SS file_count
        date_time = pd.to_datetime(' '.join(dateline.split()[:2]))
        f.readline() # type of instrument
        number_of = f.readline().split() # comment lines, variables, height levels
        Ncomments,Nvar,Nz = [ int(val) for val in number_of ]
        f.readline() # blank
        for _ in range(3): f.readline() # file information section
        for _ in range(Ncomments): f.readline()
        for _ in range(3): f.readline() # file type section
        assert(f.readline().strip() == 'Main Data')
        for _ in range(3): f.readline() # variable defintions section
        columns = []
        for _ in range(Nvar+1):
            defn = f.readline().split('#') # e.g. "wind speed # speed # m/s # G1 # 0 # 99.99"
            columns.append(defn[0].strip())
        for _ in range(3): f.readline() # beginning of data block
        f.readline()
        f.readline() # time stamp (corresponding to the end of the measurement period)
        data = np.loadtxt(f)
    df = pd.DataFrame(data=data,columns=columns)
    df['date_time'] = date_time
    df.loc[df['wind speed']==bad_speed_value,'wind speed'] = np.nan # flag bad values
    df.loc[df['wind direction']==bad_direction_value,'wind direction'] = np.nan # flag bad values
    return df


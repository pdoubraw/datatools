# readData.py
#
# Matt Churchfield
# National Renewable Energy Laboratory
# 8 May 2017
#
# This is a module that contains methods to read in data sampled from atmospheric LES.







# Read in structured VTK data.  The data is returned as a list called fields that
# contains numpy arrays.  For example, the VTK file may contain both pressure
# and temperature, or velocity and vorticity, so each quantity will be contained
# in a separate array in the list.  Then for each array, the first index is
# the number of components, so for scalars, there is only one component, but for
# vectors there will be three.  The remaining dimensions are the number of 
# sample points in x, y, and z.

def structuredVTK(fileName):
  # Import necessary modules
  import numpy as np
  
  
  # Open the file
  f = open(fileName,'r')
  
  
  # Get data set name.
  f.readline()
  dataSetName = f.readline()
  
  
  # Get data dimensions.
  f.readline()
  f.readline()
  d = f.readline()
  d = d[11:]
  c = d.split()
  dims = []
  dims.append(int(c[0]))
  dims.append(int(c[1]))
  dims.append(int(c[2]))
  dims = np.asarray(dims)
  
  
  # Get data origin.
  d = f.readline()
  d = d[7:]
  c = d.split()
  origin = []
  origin.append(float(c[0]))
  origin.append(float(c[1]))
  origin.append(float(c[2]))
  origin = np.asarray(origin)
  
  
  # Get data spacing in each direction.
  d = f.readline()
  d = d[8:]
  c = d.split()
  spacing = []
  spacing.append(float(c[0]))
  spacing.append(float(c[1]))
  spacing.append(float(c[2]))
  spacing = np.asarray(spacing)
  
  
  # Form data point structured grid.
  if (dims[0] > 1):
      x = np.linspace(origin[0],origin[0]+spacing[0]*(dims[0]-1),dims[0])
  else:
      x = np.array([1])
      x[0] = origin[0]
  if (dims[1] > 1):
      y = np.linspace(origin[1],origin[1]+spacing[1]*(dims[1]-1),dims[1])
  else:
      y = np.array([1])
      y[0] = origin[1]
  if (dims[2] > 1):
      z = np.linspace(origin[2],origin[2]+spacing[2]*(dims[2]-1),dims[2])
  else:
      z = np.array([1])
      z[0] = origin[2]
  
  
  # Read header for field data
  f.readline()
  d = f.readline()
  d = d[18:]
  nFields = int(d)
  
  
  # Read field data.
  field = []
  fieldName = []
  fieldDim = []
  for m in range(nFields):
      if (m > 0):
          f.readline()
          
      d = f.readline()
      c = d.split()
      fieldName.append(c[0])
      fieldDim.append(int(c[1]))
      dataArray = np.zeros((fieldDim[m], dims[0], dims[1], dims[2]))
      for i in range(dims[0]):
          for k in range(dims[2]):
              for j in range(dims[1]):
                  l = f.readline()
                  l = l.split()
                  for n in range(fieldDim[m]):
                      dataArray[n][i][j][k] = float(l[n])
                      
      field.append(dataArray)
  
  
  # Close file.
  f.close()
  
  
  # Return the data.
  return dataSetName, dims, origin, spacing, x, y, z, nFields, fieldName, fieldDim, field







# Read in Ensight format data.  The data is returned as a list called fields that
# contains numpy arrays.  For example, the Ensight file may contain both pressure
# and temperature, or velocity and vorticity, so each quantity will be contained
# in a separate array in the list.  Then for each array, the first index is
# the number of components, so for scalars, there is only one component, but for
# vectors there will be three.  The remaining dimensions are the number of 
# sample points in x, y, and z.

def ensight(fileNameMesh,fileNameField,readFieldOnly,dims):
  # Import necessary modules
  import numpy as np
  
  
  # Read in the geometry.
  if (readFieldOnly == 0):
      # Open the mesh file
      f = open(fileNameMesh,'r')
  
  
      # Get the data length.
      for i in range(8):
          f.readline()
      dims = int(f.readline())
      f.close()
  
  
      # Read in the x,y,z data.
      data = np.genfromtxt(fileNameMesh,skip_header=9,max_rows=dims*3)
      x = np.zeros(dims)
      y = np.zeros(dims)
      z = np.zeros(dims)
      x = data[0:dims]
      y = data[dims:2*dims]
      z = data[2*dims:3*dims]
      
      
      
      
  
    
  # Read in the field data.
  f = open(fileNameField,'r')
  
  
  # Get the data type
  fieldDim = 0
  dataType = f.readline().strip('\n')
  
  if (dataType == 'scalar'):
      fieldDim = 1
  elif (dataType == 'vector'):
      fieldDim = 3
  elif (dataType == 'tensor'):
      fieldDim = 9

  f.close()
  
      
  # Read the field
  field = np.zeros((dims,fieldDim))
  data = np.genfromtxt(fileNameField,skip_header=4,max_rows=dims*fieldDim)
  
  for i in range(fieldDim):
      field[0:dims,i] = data[i*dims:(i+1)*dims]

  
  
  # Return the data.
  return dims, x, y, z, fieldDim, field







# Read in the planar averaged data output by SOWFA.

def planarAverages(averagingDirectory,varName):
    # Import necessary modules.
    import numpy as np
    import getDataLayout


    # Find the time directories.
    [nTimes,outputTimes] = getDataLayout.getOutputTimes(averagingDirectory)
    
    
    # Read the heights file.
    z = np.genfromtxt(averagingDirectory + '/' + outputTimes[0] + '/hLevelsCell')
    
    
    # For each time directory, read the data and concatenate.
    tInt = []
    dtInt = []
    dataInt = []
    t = []
    dt = []
    data = []
    for i in range(nTimes):
        a = np.genfromtxt(averagingDirectory + '/' + outputTimes[i] + '/' + varName)
        tInt = a[:,0]
        dtInt = a[:,1]
        dataInt = a[:,2:]

        if (i < nTimes-1):
            tNext = float(outputTimes[i+1])
            index = np.argmax(np.abs(tInt >= tNext))
        else:
            index = len(tInt)
            
        if (i == 0):
            t = tInt[0:index]
            dt = dtInt[0:index]
            data = dataInt[0:index,:]
        else:
            t = np.concatenate((t,tInt[0:index]),axis=0)
            dt = np.concatenate((dt,dtInt[0:index]),axis=0)
            data = np.concatenate((data,dataInt[0:index,:]),axis=0)
    
    
    return z, t, dt, data


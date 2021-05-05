# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

import os
import base64
from io import BytesIO, StringIO
from PIL import Image


import luxpy as lx
from luxpy.toolboxes import photbiochem as ph
from luxpy.toolboxes import iolidfiles as lid 

logo = plt.imread('LUXPY_logo_new1_small.png')

__version__ = 'v0.0.25'

def spd_to_tm30(spd):
    return lx.cri._tm30_process_spd(spd, cri_type = 'ies-tm30')

def plot_tm30(data,
              source = '',
              manufacturer = '',
              date = '',
              model = '',
              notes = '',
              save_fig_name = None):
    return lx.cri.plot_tm30_report(data,
                            cri_type = 'ies-tm30',
                            source = source,
                            manufacturer = manufacturer,
                            data = date,
                            model = model,
                            notes = notes,
                            save_fig_name = save_fig_name)


def load_spectral_data():
    st.sidebar.markdown("### Load spectral data:")
    
    lspd = st.sidebar.beta_expander("Data-format options")
    lspd.checkbox("Column format", True, key = 'options')
    units = lspd.selectbox('Units',['W/nm [,.m²,.m².sr, ...]','mW/nm [,.m²,.m².sr, ...]' ])
    unit_factor = 1.0 if units == 'W/nm [,.m²,.m².sr, ...]' else 1/1000
    header = 'infer' if lspd.checkbox("Data file has header", False, key = 'header') else None
    sep = lspd.selectbox('Separator',[',','\t',';'])
    
    lspd1 = st.sidebar.beta_expander("Upload Spectral Data",True)
    uploaded_file = lspd1.file_uploader("",accept_multiple_files=False,type=['csv','dat','txt'])
    file_details = ''
    if uploaded_file is not None:
        file_details = {"FileName":uploaded_file.name,"FileType":uploaded_file.type,"FileSize":uploaded_file.size}
        df = pd.read_csv(uploaded_file, header =  header, sep = sep)
        df.iloc[:,df.columns[1]:] = df.iloc[:,df.columns[1]:] * unit_factor
        if header == 'infer':
            names = df.columns[1:]
        else:
            names = ['S{:1.0f}'.format(i+1) for i in range(len(df.columns)-1)]
        df.columns = ['nm'] + names
    else:
        df = pd.DataFrame(lx._CIE_D65.copy().T) # D65 default
        names = 'D65 (default)'
        df.columns = ['nm',names]
        
    return df, file_details, 'Graph'
    
placeholder_spdname = None
def display_spectral_input_data(df, file_details, display):
    global placeholder_spdname
    # st.sidebar.markdown("""---""")
    st.sidebar.markdown('### Input data:')
    dspd = st.sidebar.beta_expander('Show input data')   
    display = dspd.selectbox("Display format", ('Graph','DataFrame','No'))

    if display != 'No':
        #st.sidebar.title('Spectral input data')
        dspd.write(file_details)
    if display == 'No':
        pass
    elif display == 'DataFrame':
        dspd.dataframe(df)
    else:
        fig, ax = plt.subplots(figsize=(7, 3))
        plt.sca(ax)
        lx.SPD(df.values.T).plot(wavelength_bar=False, label = df.columns[1:])
        ax.legend()
        dspd.pyplot(fig)
    placeholder_spdname = st.sidebar.empty() # placeholder for spetrum name
    
def load_LID_file():
    global start
    st.sidebar.markdown("### Load LID data:")
    llid = st.sidebar.beta_expander("Upload LID (IES/LDT) data file")
    uploaded_file = llid.file_uploader("",accept_multiple_files=False,type=['ies','ldt'])
    file_details = ''
    if uploaded_file is not None:
        file_details = {"FileName":uploaded_file.name,"FileType":uploaded_file.type,"FileSize":uploaded_file.size}
        stringio = StringIO(uploaded_file.getvalue().decode("utf-8"))
        LID = lid.read_lamp_data(stringio.read(), verbosity = 1)
        start = False
        llid.write(file_details)
    else:
        LID = {}
        st.text('No LID data file selected, load file first!')
    return LID


def display_LID_file(LID):
    
        # or combine draw and render (but use only 2D image):
    if len(LID)>0:
        st.markdown('**Luminous Intensity Distiribution (polar plot and render)**')

        fig = plt.figure(figsize=[14,7])
        axs = [fig.add_subplot(121, projection = 'polar'),
               fig.add_subplot(122)]
        lid.draw_lid(LID, ax = axs[0])
        Lv2D = lid.render_lid(LID, sensor_resolution = 100,
                        sensor_position = [0,-1,0.8], sensor_n = [0,1,-0.2], fov = (90,90), Fd = 2,
                        luminaire_position = [0,1.3,2], luminaire_n = [0,0,-1],
                        wall_center = [0,2,1], wall_n = [0,-1,0], wall_width = 4, wall_height = 2, wall_rho = 1,
                        floor_center = [0,1,0], floor_n = [0,0,1], floor_width = 4, floor_height = 2, floor_rho = 1,
                        ax3D = None, ax2D = axs[1], join_axes = False, 
                        plot_luminaire_position = True, plot_lumiaire_rays = False, plot_luminaire_lid = True,
                        plot_sensor_position = True, plot_sensor_pixels = False, plot_sensor_rays = False, 
                        plot_wall_edges = True, plot_wall_luminance = True, plot_wall_intersections = False,
                        plot_floor_edges = True, plot_floor_luminance = True, plot_floor_intersections = False,
                        out = 'Lv2D')
        st.pyplot(fig)
        start = False
    else:
        start = True
    
    return start

def calculate(option, df, **kwargs):
    global start
    df_res = None
    if option == 'ANSI/IESTM30 graphic report':
        name = st.sidebar.selectbox('Select spectrum',df.columns[1:])
        index = list(df.columns[1:]).index(name)
        manufacturer = st.sidebar.text_input('Manufacturer','')
        date = st.sidebar.text_input('Date','')
        model = st.sidebar.text_input('Model','')
        notes = st.sidebar.text_input('Notes','')
        data = df.values.T[[0,index+1],:]
    elif ((option == 'Alpha-opic quantities (CIE S026)') | 
         (option == 'ANSI/IESTM30 quantities') |
         (option == 'CIE 13.3-1995 Ra, Ri quantities') |
         (option == 'CIE 224:2017 Rf, Rfi quantities'),
         (option == "SPD->(X,Y,Z), (x,y), (u',v'), (CCT,Duv)")):
        spd_opts = ['all'] + list(df.columns[1:])
        name = placeholder_spdname.selectbox('Select spectrum',spd_opts)
        if name != 'all':
            index = spd_opts.index(name) - 1
            data = df.values.T[[0,index+1],:]
            names = [df.columns[1:][index]]
        else:
            data = df.values.T
            names = df.columns[1:]
        rfl = kwargs.get('rfl',None)
    else:
        data = df.values.T
    
    st.sidebar.markdown("""---""")
    if st.sidebar.button('RUN'):
        start = False
        if option == 'ANSI/IESTM30 graphic report':
            axs, results = lx.cri.plot_tm30_report(data, 
                                                source = name, 
                                                manufacturer = manufacturer,
                                                date = date,
                                                model = model,
                                                notes = notes,
                                                save_fig_name = name)
            st.pyplot(axs['fig'])
            
            # img = plt.imread(name + '.png')
            # result = Image.fromarray((img[...,:-1]*255).astype(np.uint8))
            # st.markdown(get_image_download_link(result), unsafe_allow_html=True)
        elif option == 'ANSI/IESTM30 quantities':
            d = spd_to_tm30(data)
            LER = lx.spd_to_ler(d['St'])
            xy = lx.xyz_to_Yxy(d['xyztw_cct'])[...,1:]
            uv = lx.xyz_to_Yuv(d['xyztw_cct'])[...,1:]
            quants = ['CCT','Duv'] + ['x','y',"u'","v'",'LER'] + ['Rf', 'Rg']
            quants += ['Rcsh{:1.0f}'.format(i+1) for i in range(d['Rcshj'].shape[0])] 
            quants += ['Rhsh{:1.0f}'.format(i+1) for i in range(d['Rhshj'].shape[0])] 
            quants += ['Rfh{:1.0f}'.format(i+1) for i in range(d['Rfhj'].shape[0])]
            quants += ['Rf{:1.0f}'.format(i+1) for i in range(d['Rfi'].shape[0])]
            
            df_res = pd.DataFrame(np.vstack((d['cct'].T,d['duv'].T,
                                             xy.T,uv.T,LER.T,
                                             d['Rf'], d['Rg'],
                                             d['Rcshj'],d['Rhshj'],d['Rfhj'],d['Rfi'])).T,
                                   columns = quants,
                                   index = names)
            
            st.markdown('**ANSI/IES TM30 Quantities (CCT, Duv, Rf,Rg, ...)**')
            st.dataframe(df_res)
            
            st.markdown('*CCT: Correlated Color Temperature (K)*')
            st.markdown('*Duv: distance from Planckian locus*')
            st.markdown('*xy: CIE 1931 2° xy chromaticity coordinates of illuminant white point*')
            st.markdown("*u'v': CIE 1976 2° u'v' chromaticity coordinates*")
            st.markdown('*LER: Luminous Efficacy of Radiation (lm/W)*')
            st.markdown('*Rf: general color fidelity index*')
            st.markdown('*Rg: gamut area index*')
            st.markdown('*Rcshj: local chroma shift for hue bin j*')
            st.markdown('*Rhshj: local hue shift for hue bin j*')
            st.markdown('*Rfhj: local color fidelity index for hue bin j*')
            st.markdown('*Rfi: specific color fidelity index for sample i*')
        
        elif option == 'CIE 13.3-1995 Ra, Ri quantities':
            d = spd_to_tm30(data)
            LER = lx.spd_to_ler(d['St'])
            Ra, _ = lx.cri.spd_to_cri(d['St'], cri_type = 'ciera', out = 'Rf,Rfi')
            _, Ri = lx.cri.spd_to_cri(d['St'], cri_type = 'ciera-14', out = 'Rf,Rfi')

            xy = lx.xyz_to_Yxy(d['xyztw_cct'])[...,1:]
            uv = lx.xyz_to_Yuv(d['xyztw_cct'])[...,1:]
            quants = ['CCT','Duv'] + ['x','y',"u'","v'",'LER'] + ['Ra']
            quants += ['R{:1.0f}'.format(i+1) for i in range(Ri.shape[0])]
            
            df_res = pd.DataFrame(np.vstack((d['cct'].T,d['duv'].T,
                                             xy.T,uv.T,LER.T,
                                             Ra, Ri)).T,
                                   columns = quants,
                                   index = names)
            
            st.markdown('**CIE 13.3-1995 Ra, Ri quantities**')
            st.dataframe(df_res)
            
            st.markdown('*CCT: Correlated Color Temperature (K)*')
            st.markdown('*Duv: distance from Planckian locus*')
            st.markdown('*xy: CIE 1931 2° xy chromaticity coordinates of illuminant white point*')
            st.markdown("*u'v': CIE 1976 2° u'v' chromaticity coordinates*")
            st.markdown('*LER: Luminous Efficacy of Radiation (lm/W)*')
            st.markdown('*Ra: general color fidelity index*')
            st.markdown('*Ri: specific color fidelity index for sample i*')
  
        elif option == 'CIE 224:2017 Rf, Rfi quantities':
            d = spd_to_tm30(data)
            LER = lx.spd_to_ler(d['St'])
            Ra,Ri = lx.cri.spd_to_cierf(d['St'], out = 'Rf,Rfi')
            xy = lx.xyz_to_Yxy(d['xyztw_cct'])[...,1:]
            uv = lx.xyz_to_Yuv(d['xyztw_cct'])[...,1:]
            quants = ['CCT','Duv'] + ['x','y',"u'","v'",'LER'] + ['Rf']
            quants += ['Rf{:1.0f}'.format(i+1) for i in range(Ri.shape[0])]
            
            df_res = pd.DataFrame(np.vstack((d['cct'].T,d['duv'].T,
                                             xy.T,uv.T, LER.T,
                                             Ra, Ri)).T,
                                   columns = quants,
                                   index = names)
            
            st.markdown('**CIE 224:2017 Rf, Rfi quantities**')
            st.dataframe(df_res)
            
            st.markdown('*CCT: Correlated Color Temperature (K)*')
            st.markdown('*Duv: distance from Planckian locus*')
            st.markdown('*xy: CIE 1931 2° xy chromaticity coordinates of illuminant white point*')
            st.markdown("*u'v': CIE 1976 2° u'v' chromaticity coordinates*")
            st.markdown('*LER: Luminous Efficacy of Radiation (lm/W)*')
            st.markdown('*Rf: general color fidelity index*')
            st.markdown('*Rfi: specific color fidelity index for sample i*')

    
        elif option == 'Alpha-opic quantities (CIE S026)':
            try:
                # alpha-opic Ee, -EDI, -DER and -ELR:
                cieobs = '1931_2'
                aEe = ph.spd_to_aopicE(data,cieobs = cieobs,actionspectra='CIE-S026',out = 'Eeas')
     
                aedi = ph.spd_to_aopicEDI(data,cieobs = cieobs,actionspectra='CIE-S026')
                ader = ph.spd_to_aopicDER(data, cieobs = cieobs,actionspectra='CIE-S026')
                aelr = ph.spd_to_aopicELR(data, cieobs = cieobs,actionspectra='CIE-S026')
                results = {'a-EDI':aedi,'aDER':ader,'aELR':aelr}
                
                quants = ['a-Ee','a-EDI','a-DER','a-ELR']
                tmp_q = np.repeat(quants,len(names))
                tmp_n = np.tile(names,len(quants))
                df_indices = ['{:s}: {:s}'.format(quant,name) for name,quant in zip(tmp_n,tmp_q)]
                df_res = pd.DataFrame(np.vstack((aEe,aedi,ader,aelr)), 
                                      columns = ph._PHOTORECEPTORS,
                                      index = df_indices)
                
                st.markdown('**alpha-opic quantities (CIE S026)**')
                st.dataframe(df_res)
                
                st.markdown('*Ee: irradiance (W/m²)*')
                st.markdown('*EDI: Equivalent Daylight Illuminance (lux)*')
                st.markdown('*DER: Daylight Efficacy Ratio*')
                st.markdown('*ELR: Efficacy of Luminous Radiation (W/lm)*')
                
            except:
                st.markdown('Not implemented yet (03/05/2021)')
                
        elif option == "SPD->(X,Y,Z), (x,y), (u',v'), (CCT,Duv)":
            if rfl is not None:
                xyz, xyzw = lx.spd_to_xyz(data, cieobs = kwargs['cieobs'], relative = kwargs['relative_xyz'], rfl = kwargs['rfl'])
            else:
                xyz = lx.spd_to_xyz(data, cieobs = kwargs['cieobs'], relative = kwargs['relative_xyz'])
            cct, duv = lx.xyz_to_cct(xyz, out ='cct,duv')
            xy = lx.xyz_to_Yxy(xyz)[...,1:]
            uv = lx.xyz_to_Yuv(xyz)[...,1:]
            quants = ['X','Y','Z'] + ['x','y',"u'","v'"] + ['CCT','Duv']
            
            df_res = pd.DataFrame(np.vstack((xyz.T,
                                             xy.T,uv.T,
                                             cct.T, duv.T,
                                             )).T,
                                   columns = quants,
                                   index = names)
            
            st.markdown("**(X,Y,Z), (x,y), (u',v'), (CCT,Duv) for CIE observer {:s}**".format(kwargs['cieobs']))
            st.dataframe(df_res)
            st.markdown('*XYZ: CIE X,Y,Z tristimulus values*')
            st.markdown('*xy: CIE xy chromaticity coordinates*')
            st.markdown("*u'v': CIE 1976 u'v' chromaticity coordinates*")
            st.markdown('*CCT: Correlated Color Temperature (K)*')
            st.markdown('*Duv: distance from Planckian locus*')

    else:
        start = False
        data = []
    return data, start, df_res
 
    
def get_table_download_link_csv(df):
    csv = df.to_csv().encode()
    b64 = base64.b64encode(csv).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="luxpy_app_download.csv" target="_blank">Download csv file</a>'
    return href

start = True           
            
def main():
    global start 
    df_download = None
    st.sidebar.image(logo, width=300)
    st.sidebar.markdown('## **Online calculator for lighting and color science**')
    st.sidebar.markdown('Luxpy {:s}, App {:s}'.format(lx.__version__, __version__))
    link = 'Code: [github.com/ksmet1977/luxpy](http://github.com/ksmet1977/luxpy)'
    st.sidebar.markdown(link, unsafe_allow_html=True)
    st.sidebar.markdown('Code author: Prof. dr. K.A.G. Smet')
    # st.sidebar.markdown("""---""")
    st.sidebar.title('Control panel')
    option = st.sidebar.selectbox("Calculation options", ('',
                                                          'ANSI/IESTM30 quantities', 
                                                          'ANSI/IESTM30 graphic report',
                                                          'CIE 13.3-1995 Ra, Ri quantities',
                                                          'CIE 224:2017 Rf, Rfi quantities',
                                                          'Alpha-opic quantities (CIE S026)',
                                                          "SPD->(X,Y,Z), (x,y), (u',v'), (CCT,Duv)",
                                                          'Plot Luminous Intensity Distribution (IES/LDT files)'
                                                          ))
    st.sidebar.markdown("""---""")
    if option in ('ANSI/IESTM30 quantities',
                  'ANSI/IESTM30 graphic report',
                  'CIE 13.3-1995 Ra, Ri quantities',
                  'CIE 224:2017 Rf, Rfi quantities',
                  'Alpha-opic quantities (CIE S026)'):
        df, file_details, display = load_spectral_data()
        display_spectral_input_data(df, file_details, display)
        data, start, df_download = calculate(option, df)
    elif (option == "SPD->(X,Y,Z), (x,y), (u',v'), (CCT,Duv)"):
        df, file_details, display = load_spectral_data()
        display_spectral_input_data(df, file_details, display)
        # st.sidebar.markdown("""---""")
        st.sidebar.markdown("### XYZ options:")
        cieobs = st.sidebar.selectbox('CIE observer',[x for x in lx._CMF['types'] if (x!='cie_std_dev_obs_f1')])
        relative_xyz = st.sidebar.checkbox("Relative XYZ [Ymax=100]", True, key = 'relative_xyz')
        data, start, df_download = calculate(option, df, cieobs = cieobs, relative_xyz = relative_xyz)
    elif option in ('Plot Luminous Intensity Distribution (IES/LDT files)',):
        lid_dict = load_LID_file()
        st.sidebar.markdown("""---""")
        if st.sidebar.button('RUN'):
            start = display_LID_file(lid_dict)
    else:
        df, file_details, display = None, {}, 'No'
     
    if (option != '') &  (start):
       st.text('Scroll down control panel...')

        
    if start:
        st.markdown('### Usage:')
        st.markdown(' 1. Select calculation option.')
        st.markdown(' 2. Load data (set) (and set data format options; default = csv in column format.')
        st.markdown(' 3. Press RUN.')
    
    if df_download is not None:
        st.markdown("""---""")
        st.markdown(get_table_download_link_csv(df_download), unsafe_allow_html=True)    
    st.markdown("""---""")
    st.markdown("If you use **LUXPY**, please cite the following tutorial paper published in LEUKOS:")
    st.markdown("**Smet, K. A. G. (2019). Tutorial: The LuxPy Python Toolbox for Lighting and Color Science. LEUKOS, 1–23.** DOI: [10.1080/15502724.2018.1518717](https://doi.org/10.1080/15502724.2018.1518717)")
    st.markdown("""---""")
    #start = False
    
if __name__ == '__main__':
    main()
    
    
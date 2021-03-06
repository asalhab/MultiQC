#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" MultiQC module to parse output from deepTools """

from __future__ import print_function
import logging
from multiqc import config
from multiqc.modules.base_module import BaseMultiqcModule
from multiqc.plots import table, bargraph, linegraph, scatter
from . import heatmap
import math
import numpy as np
import collections 
import random

#Initialise the logger
log = logging.getLogger(__name__)

class MultiqcModule(BaseMultiqcModule):
    """
    deepTools module class, parses deepTools logs.
    """

    def __init__(self):

        #Initialise the parent object
        super(MultiqcModule, self).__init__(name='deepTools', anchor='deepTools',
        href='http://deeptools.readthedocs.io/en/latest/',
        info="is a set of tools for exploring deep sequencing data. particularly developed for the efficient analysis of ChIP-seq, RNA-seq or MNase-seq.")

        #Start the sections
        self.sections = list()


        #correlation heatmap plot
        n = dict()
        n['Corr'] = heatmap.parse_reports(self)
        if n['Corr'] > 0:
            log.info("Found {} Correlation reports".format(n['Corr']))
        



        #PCA Plots
        num_pca = 0
        self.PCA_data = dict()
        self.PCA_Eigen = dict()
        self.PCA_comp = dict()

        for f in self.find_log_files(config.sp['deepTools']['PCA'], filehandles = True):
            self.parsePCA(f)
            num_pca+=1
        if len(self.PCA_data) > 0:
            self.deepToolsPCAPlot()
            self.deepToolsCompPlot()
            self.add_data_source(f, section='PCA')


        if num_pca == 1:
            log.info("Found {} PCA reports for {} samples".format(num_pca, len(self.PCA_data)))
        elif num_pca > 1:
            log.warning("Found {} PCA reports. Only one PCA file is allowed! Overwriting".format(num_pca))


        

        #Coverage plots
        num_cov = 0
        self.coverage_data = dict()
        self.cumulative_data = dict()

        for f in self.find_log_files(config.sp['deepTools']['coverage'], filehandles = True):
            self.parseCoverage(f)
            num_cov+=1

        if len(self.coverage_data) > 0:
            self.deepToolsCoveragePlot()
            self.add_data_source(f, section='coverage')

        if num_cov == 1:
            log.info("Found {} Coverage reports for {} samples".format(num_cov, len(self.coverage_data)))
        elif num_cov > 1:
            log.warning("Found {} coverage reports. Only one coverage file is allowed! Overwriting".format(num_cov))




        #gc_bias plots
        num_gc = 0
        self.gc_bias_data = dict()

        for f in self.find_log_files(config.sp['deepTools']['gc_bias'], filehandles = True):
            self.parseGCBias(f)
            num_gc+=1

        if len(self.gc_bias_data) > 0:
            self.deepToolsGCBiasPlot()
            self.add_data_source(f, section='GCBias')
            log.info("Found {} GC Bias reports".format(num_gc))




        #fingerPrint plots
        num_fgpr = 0
        self.fgpr_data = dict()

        for f in self.find_log_files(config.sp['deepTools']['fgpr'], filehandles = True):
            self.parseFingerPrint(f)
            num_fgpr+=1

        if len(self.fgpr_data) > 0:
            self.deepToolsFingerPrintPlot()
            self.add_data_source(f, section='fgpr')

        if num_fgpr == 1:
            log.info("Found {} FingerPrint reports for {} samples".format(num_fgpr, len(self.fgpr_data)))
        elif num_fgpr > 1:
            log.warning("Found {} FingerPrint reports. Only one FingerPrint file is allowed! Overwriting".format(num_fgpr))



    def parsePCA(self, f):
        fields = zip(*(line.strip().split() for line in f['f']))
 
        #exclude the first and last column;i.e, Components and Eigenvalues
        for i in fields[1:-1]:
            sample = i[0]
            PC1 = i[1]
            PC2 = i[2]
            self.PCA_data[sample] = [{'x': float(PC1), 'y': float(PC2)}]


        #generate the Eigenvalues data structure for lineplot
        for i in range(0,len(fields[0])):
            if len(self.PCA_Eigen.keys())==0:
                self.PCA_Eigen[f['s_name'].split(".")[0]] = dict()
            else:
                self.PCA_Eigen[f['s_name'].split(".")[0]].update({int(fields[0][i]):float(fields[len(fields[0])][i])})
                


        #generate the PC contributions data structure for lineplot 
        total = 0
        sums = dict()

        for i in range(1,len(fields[0])):
            total = total + float(fields[len(fields[0])][i])
            if len(sums.keys()) == 0:
                sums[f['s_name'].split(".")[0]] = {int(i):total}
            else:
                sums[f['s_name'].split(".")[0]].update({int(i):total})

        for i in range(1,len(fields[0])):
            if len(self.PCA_comp.keys()) == 0:
                self.PCA_comp[f['s_name'].split(".")[0]] = {int(i):sums[f['s_name'].split(".")[0]][i]/total}
            else:
                self.PCA_comp[f['s_name'].split(".")[0]].update({int(i):sums[f['s_name'].split(".")[0]][i]/total})




    def parseCoverage(self, f):
        header=next(f['f'])
        names=header.split()[3:]
        self.coverage_data=dict([(key, {}) for key in names])
        self.cumulative_data=dict([(key, {}) for key in names])
        fields = zip(*(line.strip().split() for line in f['f']))
        fields = fields[3:]

        x = [[float(y) for y in fields[i]] for i in range(0,len(fields))]
        #x=[]
        #for i in range(0,len(fields)):
            #x.append([float(y) for y in fields[i]])

        counter = [collections.Counter(i) for i in x]

        total = [sum(i.values()) for i in counter]

        frac = [[float(y)/total[i] for y in counter[i].values()] for i in range(0,len(counter))]

        accum = [1-np.cumsum(frac[i]) for i in range(0,len(frac))]


        for i in range(0,len(self.coverage_data)):
            for j in range(0,len(frac[i])):
                self.coverage_data[names[i]].update({counter[i].keys()[j]:frac[i][j]})

        for i in range(0,len(self.cumulative_data)):
            for j in range(0,len(accum[i])):
                self.cumulative_data[names[i]].update({counter[i].keys()[j]:accum[i][j]})

            self.cumulative_data[names[i]].update({0:1})



    def parseGCBias(self, f):
        sample = f['s_name'] #sample = f['s_name'].split(".")[0]
        count = 0
        
        fields = zip(*(line.strip().split() for line in f['f']))
        x = [float(y)/len(fields[2]) for y in range(0,len(fields[2]),1)]
        y = [math.log(float(y),2) for y in fields[2]]
        d = dict()
        for i in range(0, len(x)):
            d[x[i]] = y[i]

        if sample not in self.gc_bias_data:
            self.gc_bias_data[sample] = d



    def parseFingerPrint(self, f):
        #extract the names from the first line
        header=next(f['f'])
        names=header.split()
        self.fgpr_data=dict([(key, {}) for key in names])
        fields = zip(*(line.strip().split() for line in f['f']))

        #randomly choose 10000 points since the number of points is very large
        fields = [random.sample(x,10000) for x in fields]

        x=[]
        for i in range(0,len(fields)):
            x.append([float(y) for y in fields[i]])

        xsum=[np.cumsum(np.sort(np.array(y))) for y in x] #sort and cumulative sum calculation
        xNor=[y/y[-1] for y in xsum]  #normalize between 0 and 1
        total = len(fields[0])
        bins = np.arange(total).astype('float') / total

        for i in range(0,len(self.fgpr_data)):
            for j in range(0,len(fields[0])):
                self.fgpr_data[names[i]].update({bins[j]:xNor[i][j]})



    def deepToolsPCAPlot(self):
        """ Generate the PCA plots """
        pconfig = {
            'id': 'deepTools_pca',
            'title': 'PCA',
            'xlab': 'PC1',
            'ylab': 'PC2',
            'tt_label': 'PC1 {point.x:.2f}: PC2 {point.y:.2f}',
            'square': True
        }
        self.sections.append({
            'name': 'PCA',
            'anchor': 'deepTools_PCA',
            'content': '<p> This plot was generated by <a href="http://deeptools.readthedocs.io/en/latest/content/tools/plotPCA.html" target="_blank">plotPCA</a> and shows the principal components of samples based on the output of ' + '<a href="http://deeptools.readthedocs.io/en/latest/content/tools/multiBamSummary.html" target="_blank">multiBamSummary</a> or ' + '<a href="http://deeptools.readthedocs.io/en/latest/content/tools/multiBigwigSummary.html" target="_blank">multiBigwigSummary</a>' + '</p>' + scatter.plot(self.PCA_data, pconfig) 
        })


    def deepToolsCompPlot(self):
        """ Generate the PC contributions plots """
        pconfig = {
            'id': 'deepTools_pca_comp',
            'title': 'PC Contributions',
            'xlab': 'Comp',
            'xDecimals': False,
            'ymin': 0,
            'tt_label': '{point.x} : {point.y:.2f}',
            'data_labels': [
                {'name': 'PC contribution', 'ylab': 'cumulative variability'},
                {'name': 'Eigenvalues', 'ylab': 'Eigenvalues'}
            ]
        }
        self.sections.append({
            'name': 'PCA_Comp',
            'anchor': 'deepTools_PCA_Comp',
            'content': '<p> This plot was generated by <a href="http://deeptools.readthedocs.io/en/latest/content/tools/plotPCA.html" target="_blank">plotPCA</a> and shows the principal components of samples based on the output of ' + '<a href="http://deeptools.readthedocs.io/en/latest/content/tools/multiBamSummary.html" target="_blank">multiBamSummary</a> or ' + '<a href="http://deeptools.readthedocs.io/en/latest/content/tools/multiBigwigSummary.html" target="_blank">multiBigwigSummary</a>' + '</p>' + linegraph.plot([self.PCA_comp, self.PCA_Eigen], pconfig)
        })


    def deepToolsCoveragePlot(self):
        """ Generate the Coverage plots """
        pconfig = {
            #'id': 'deepTools_coverage', for some reasons, with this parameter, the plot was not shown
            #'title': 'Read Coverage',
            'xlab': 'Read Coverage',
            'xmax': 120,
            'data_labels': [
                {'name': 'coverage', 'ylab': 'fraction of bases sampled'},
                {'name': 'cumulative', 'ylab': 'fraction of bases sampled >= coverage', 'ymax': 1, 'ymin': 0}
            ]
        }
        self.sections.append({
            'name': 'Coverage',
            'anchor': 'deepTools_coverage',
            'content': '<p> This plot was generated by <a href="http://deeptools.readthedocs.io/en/latest/content/tools/plotCoverage.html" target="_blank">plotCoverage</a> to assess the sequencing depth of a given sample. The first one simply represents the frequencies of the found read coverages. The second plot helps you answer the question what is the fraction of the genome that has a depth of sequencing of 2, 5, . . . . ?</p>' + linegraph.plot([self.coverage_data, self.cumulative_data], pconfig)
        })


    def deepToolsGCBiasPlot(self):
        """ Generate the GC Bias plots """
        pconfig = {
            #'id': 'deepTools_gc_bias',
            'title': 'normalized observed/expected read counts',
            'xlab' : 'GC fraction',
            'ylab': 'log2ratio observed/expected',
            'xPlotBands': [{'color': '#FCFFC5', 'from': 0.2, 'to': 0.7}],
        }
        self.sections.append({
            'name': 'GC Bias',
            'anchor': 'deepTools_gc_bias',
            'content': '<p> This plot was generated by <a href="http://deeptools.readthedocs.io/en/latest/content/tools/computeGCBias.html" target="_blank">computeGCBias</a> using Benjamini’s method <a href="https://www.ncbi.nlm.nih.gov/pmc/articles/PMC3378858/" target="_blank">Benjamini & Speed (2012) </a> </p>' + linegraph.plot(self.gc_bias_data, pconfig)
        })


    def deepToolsFingerPrintPlot(self):
        """ Generate the FingerPrint plots """
        pconfig = {
            #'id': 'deepTools_fgpr',
            'title': 'FingerPrints',
            'xlab' : 'rank',
            'ylab': 'fraction w.r.t bin with highest coverage',
            'ymax': 1,
        }
        self.sections.append({
            'name': 'Fingerprint',
            'anchor': 'deepTools_fgpr',
            'content': '<p> This plot was generated by <a href="http://deeptools.readthedocs.io/en/latest/content/tools/plotFingerprint.html" target="_blank">plotFingerprint</a>. It determines how well the signal in the ChIP-seq sample can be differentiated from the background distribution of reads in the control sample and give a hint whether the signal is narrow or broad.</p>' + linegraph.plot(self.fgpr_data, pconfig)
        })

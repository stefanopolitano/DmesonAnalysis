'''
python script for the computation of the production cross section of prompt or feed-down D
run: python ComputeDataDrivenCrossSection.py rawYieldFile.root effAccFile.root fracFile.root outFile.root
[--prompt] [--FD] [--Dplus] [--Ds] [--system] [--energy]
prompt or FD and Dplus or Ds must be specified
'''

import argparse
import numpy as np
from ROOT import TFile, TCanvas  # pylint: disable=import-error,no-name-in-module
from utils.AnalysisUtils import ComputeCrossSection
from utils.StyleFormatter import SetGlobalStyle

parser = argparse.ArgumentParser(description='Arguments to pass')
parser.add_argument('rawYieldFileName', metavar='text',
                    default='rawYieldFile.root', help='root file with raw yields')
parser.add_argument('effAccFileName', metavar='text', default='effAccFile.root',
                    help='root file with efficiency and acceptance')
parser.add_argument('fracFileName', metavar='text',
                    default='fracFile.root', help='root file with prompt (FD) fraction')
parser.add_argument('--system', metavar='text', default='pp', help='collision system (pp, pPb, PbPb)')
parser.add_argument('--energy', metavar=float, default=5.02, help='energy (5.02)')
parser.add_argument("--prompt", action='store_true', help='flag to compute prompt cross section', default=False)
parser.add_argument("--FD", action='store_true', help='flag to compute FD cross section', default=False)
parser.add_argument("--Dplus", action='store_true', help='flag to compute D+ cross section', default=False)
parser.add_argument("--Ds", action='store_true', help='flag to compute Ds cross section', default=False)
args = parser.parse_args()

# TODO: add systematic uncertainties (create DB as AliHFSystErr? Read uncertainties from AliHFSystErr?)
# Protections for arguments
if args.system == 'pp':
    if args.energy == 5.02:
        sigmaMB = 50.87e+9 # pb
    else:
        print(f'Energy {args.energy} not implemented! Exit')
        exit()
elif args.system == 'PbPb':
    if args.energy == 5.02:
        sigmaMB = 1. # yields in case of PbPb
    else:
        print(f'Energy {args.energy} not implemented! Exit')
        exit()

if args.Dplus:
    BR = 0.0898
elif args.Ds:
    BR = 0.0227
else:
    print('ERROR: Dplus or Ds must be specified! Exit')
    exit()

# load input file
rawYieldFile = TFile.Open(args.rawYieldFileName)
hRawYields = rawYieldFile.Get('hRawYields')
hEvForNorm = rawYieldFile.Get('hEvForNorm')
nEv = hEvForNorm.GetBinContent(1)

effAccFile = TFile.Open(args.effAccFileName)
hEffAccPrompt = effAccFile.Get('hEffAccPrompt')
hEffAccFD = effAccFile.Get('hEffAcFD')

fracFile = TFile.Open(args.fracFileName)
hCorrYieldPrompt = fracFile.Get('hCorrYieldPrompt')
hCorrYieldFD = fracFile.Get('hCorrYieldFD')
hCovPromptPrompt = fracFile.Get('hCovPromptPrompt')
hCovPromptFD = fracFile.Get('hCovPromptFD')
hCovFDFD = fracFile.Get('hCovFDFD')
hCovFDPrompt = fracFile.Get('hCovFDPrompt')

# TODO: improve protection checking the limits of the bins besides the number
if hRawYields.GetNbinsX() != hEffAccPrompt.GetNbinsX() or hRawYields.GetNbinsX() != hCorrYieldPrompt.GetNbinsX():
    print('ERROR: inconsistent number of bins in input objects! Exit')

hCrossSection = hRawYields.Clone('hCrossSection')
hCrossSection.SetTitle(';#it{p}_{T} (GeV/#it{c}); d#sigma/d#it{p}_{T} (#mub GeV^{-1} #it{c})')

hPromptFrac = hEffAccPrompt.Clone('hPromptFrac')
hFDFrac = hEffAccFD.Clone('hFDFrac')
hPromptFrac.SetTitle(';#it{p}_{T} (GeV/#it{c}); #it{f}_{prompt}')
hFDFrac.SetTitle(';#it{p}_{T} (GeV/#it{c}); #it{f}_{FD}')

for iPt in range(hCrossSection.GetNbinsX()):
    ptMin = hRawYields.GetBinLowEdge(iPt+1)
    ptMax = ptMin+hRawYields.GetBinWidth(iPt+1)
    rawYield = hRawYields.GetBinContent(iPt+1)
    rawYieldUnc = hRawYields.GetBinError(iPt+1)
    effAccPrompt = hEffAccPrompt.GetBinContent(iPt+1)
    effAccFD = hEffAccFD.GetBinContent(iPt+1)

    # ingredients for (prompt or FD) fraction computation
    corrYieldPrompt = hCorrYieldPrompt.GetBinContent(iPt+1)
    corrYieldFD = hCorrYieldFD.GetBinContent(iPt+1)
    covPromptPrompt = hCovPromptPrompt.GetBinContent(iPt+1)
    covPromptFD = hCovPromptFD.GetBinContent(iPt+1)
    covFDFD = hCovFDFD.GetBinContent(iPt+1)
    covFDPrompt = hCovFDPrompt.GetBinContent(iPt+1)

    # prompt fraction
    fPrompt = effAccPrompt * corrYieldPrompt / (effAccPrompt * corrYieldPrompt + effAccFD * corrYieldFD)
    defPdeNP = (effAccPrompt * (effAccPrompt * corrYieldPrompt + effAccFD * corrYieldFD) - effAccPrompt**2
                * corrYieldPrompt) / (effAccPrompt * corrYieldPrompt + effAccFD * corrYieldFD)**2
    defPdeNF = - effAccFD * effAccPrompt * corrYieldPrompt / \
        (effAccPrompt * corrYieldPrompt + effAccFD * corrYieldFD)**2
    fPromptUnc = np.sqrt(defPdeNP**2 * covPromptPrompt + defPdeNF**2 * covFDFD + \
        2 * defPdeNP * defPdeNF * covPromptFD)

    # feed-down fraction
    fFD = effAccFD * corrYieldFD / (effAccPrompt * corrYieldPrompt + effAccFD * corrYieldFD)
    defFdeNF = (effAccFD * (effAccFD * corrYieldFD + effAccPrompt * corrYieldPrompt) - effAccFD**2
                * corrYieldFD) / (effAccPrompt * corrYieldPrompt + effAccFD * corrYieldFD)**2
    defFdeNP = - effAccFD * effAccPrompt * corrYieldFD / \
        (effAccPrompt * corrYieldPrompt + effAccFD * corrYieldFD)**2
    fFDUnc = np.sqrt(defFdeNF**2 * covFDFD + defFdeNP**2 * covPromptPrompt + \
        2 * defFdeNF * defFdeNP * covPromptFD)


    hPromptFrac.SetBinContent(iPt+1, fPrompt)
    hPromptFrac.SetBinError(iPt+1, fPromptUnc)
    hFDFrac.SetBinContent(iPt+1, fFD)
    hFDFrac.SetBinError(iPt+1, fFDUnc)

    if args.prompt:
        effAcc = effAccPrompt
        frac = fPrompt
    else:
        effAcc = hEffAccFD.GetBinContent(iPt+1)
        frac = fFD

    crossSec, crossSecUnc = ComputeCrossSection(rawYield, rawYieldUnc, effAcc, 1., ptMax-ptMin, 1., sigmaMB, nEv, BR)
    hCrossSection.SetBinContent(iPt+1, crossSec)
    hCrossSection.SetBinError(iPt+1, crossSecUnc)

SetGlobalStyle()
cCrossSec = TCanvas('cCrossSec', '', 700, 800)
hCrossSection.Draw()

cFrac = TCanvas('cFrac', '', 800, 800)
cFrac.DrawFrame(hPromptFrac.GetBinLowEdge(1), 0., ptMax, 1., ';#it{p}_{T} (GeV/#it{c}); fraction')
hPromptFrac.Draw('same')
hFDFrac.Draw('same')

cEff = TCanvas('cEff', '', 800, 800)
cEff.DrawFrame(hPromptFrac.GetBinLowEdge(1), 1.e-4, ptMax, 1., ';#it{p}_{T} (GeV/#it{c}); (Acc#times#font[152]{e})')
hEffAccPrompt.Draw('same')
hEffAccFD.Draw('same')

outFile = TFile(args.outFileName)
hCrossSection.Write()
hRawYields.Write()
hEffAccPrompt.Write()
hEffAccFD.Write()
hPromptFrac.Write()
hFDFrac.Write()
hEvForNorm.Write()
cCrossSec.Write()
cFrac.Write()
cEff.Write()
outFile.Close()

input('Press enter to exit')

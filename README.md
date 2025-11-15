# BFD9000

Contrary to popular belief, the BFD9000 stands for Bolton Files Dicomizer 9000. 9000 is just a huge version number, which is supposed to be intimidating.

Tools and processes to convert the Bolton-Brush Collection to digital format.

## Background

The Bolton Brush Growth Study Collection encompasses various types of X-rays, including lateral and poster-anterior X-rays of the cranium, as well as X-rays of the hands, wrists, elbows, knees, chest, pelvis, foot, and ankle, gathered from over 4000 subjects. This comprehensive collection also consists of dental cast models and paper charts, serving as a valuable resource for studying human growth and development. The majority of X-rays were collected in the 1930s, but the collection extended until the 1980s. To safeguard these valuable assets, approximately 500,000 X-ray films have been scanned and digitized over time.

Due to the vast scale of this project, numerous researchers, volunteers, and workers have participated. Consequently, the resulting x-rays were often saved in manually generated folders, leading to many inconsistencies in formatting and organization. The aim of this project is to provide tools for:

1. **Cleaning up the existing, scanned data:** This includes orienting all images consistently, dividing images that were collected on the same film, and saving them in a format intended for medical images (DICOM).
2. **Ensuring that the clean-up will be maintained in the future** with new scans, preserving the integrity and usability of the collection.

## Methods

We have chosen to use a neural network for correctly categorizing the images, determining their correct orientation, and identifying if and how to split them. A detailed explanation of the algorithms used can be found in the `documentation/` folder within this repository.

The tools will also likely include a GUI for the operator, assisting them in adding new scans consistently and avoiding the reintroduction of inconsistencies that were previously cleaned up.

## Future Uses

Other collections, such as [the ones in the AAOF Legacy Collection](https://www.aaoflegacycollection.org/), may also benefit from these tools. If needed, they can utilize them to achieve an organization based on an open standard like DICOM. This uniform approach could greatly enhance the research community's access to consistent and standardized datasets.

## Repository Structure

- `bfd9000_web/`: Django application for managing and viewing the BFD9000 data.
  To run the application, follow the instructions in `bfd9000_web/README.md`.

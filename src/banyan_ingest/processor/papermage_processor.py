from papermage.magelib import Document
from papermage.recipes import CoreRecipe
from papermage.visualizers.visualizer import plot_entities_on_page
import pathlib
import numpy as np

from .processor import Processor
from ..output.papermage_output import PaperMageOutput

class PaperMageProcessor(Processor):
    
    def __init__(self):
        super().__init__()
        self.recipe = CoreRecipe()

    def process_document(self, mode, filepath, options=None, colors=None):
        pdf_path = pathlib.Path(filepath)

        if mode == 'bound_single':
            output = []

            doc = self.recipe.from_pdf(pdf=pdf_path)

            for page_num, page in enumerate(doc.pages):
                intersect_dict = {}

                for option in options:
                    intersect_dict[option] = page.intersect_by_box(option)

                plotted = plot_entities_on_page(page_image=doc.images[page_num], entities=intersect_dict[options[0]], box_color=colors[0])

                for idx, option in enumerate(options[1:]):
                    plotted = plot_entities_on_page(page_image=plotted, entities=intersect_dict[option], box_color=colors[idx])
                    
                output.append(plotted)

        elif mode == 'extract_single':
            output = self.recipe.run(pdf_path)
            
        return PaperMageOutput(output)


    def process_batch_documents(self, mode, filepaths, options=None, colors=None):
        parent_path = pathlib.Path(filepaths)
        file_list = list(pathlib.Path(parent_path).glob('*.pdf'))

        if mode == 'bound_batch':
            output = {}

            for filename in file_list:
                filename_strip = str(filename.name).replace('.pdf', '')
                output[filename_strip] = []

                doc = self.recipe.from_pdf(pdf=filename)

                for page_num, page in enumerate(doc.pages):
                    intersect_dict = {}

                    for option in options:
                        intersect_dict[option] = page.intersect_by_box(option)

                    plotted = plot_entities_on_page(page_image=doc.images[page_num], entities=intersect_dict[options[0]], box_color=colors[0])

                    for idx, option in enumerate(options[1:]):
                        plotted = plot_entities_on_page(page_image=plotted, entities=intersect_dict[option], box_color=colors[idx])
                    
                    output[filename_strip].append(plotted)

        elif mode == 'extract_batch':
            output = {}

            for filename in file_list:
                filename_strip = str(filename.name).replace('.pdf', '')
                output[filename_strip]=self.recipe.run(filename)

        return PaperMageOutput(output)
    
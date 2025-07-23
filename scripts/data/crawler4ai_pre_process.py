import os
from config import *
from utility import ProcessingManager

raw_base_path = "data/school_raw"
parsed_base_path = "data/parsed_x"
empty_log_path = "data/parsed/_empty.txt"
if not os.path.exists(parsed_base_path): os.makedirs(parsed_base_path)

def run():
    file_paths = []
    for folder_name in os.listdir(raw_base_path):
        folder_path = os.path.join(raw_base_path, folder_name)
        parsed_folder = os.path.join(parsed_base_path, folder_name)
        if not os.path.exists(parsed_folder): os.mkdir(parsed_folder)
        for file_name in os.listdir(folder_path):
            file_paths.append(os.path.join(folder_name, file_name.split(".")[0]))
    file_provider = lambda tid: FileProvider(raw_base_path)
    file_consumer = lambda tid: FileConsumer(parsed_base_path)
    cmd_logger = lambda tid:CmdLogger()
    simple_processor = lambda tid:Crawler4AIProcessor() # Just diffirent in this line
    manager = ProcessingManager(
        num_workers=4,
        concurrent_per_worker=4,
        ids=file_paths,
        provider_factory=file_provider,
        consumer_factory=file_consumer,
        processor_factory=simple_processor,
        logger_factory=cmd_logger
    )
    manager.run()


if __name__ == "__main__":
    run()
import os


def create_dir(context, dir_path, *dir_name):
    full_dir_path = os.path.join(dir_path, *dir_name)
    try:
        if os.path.exists(full_dir_path):
            context.log.warn(f'{dir_name} folder already exists')
            return True
        else:
            os.mkdir(full_dir_path)
            return True
    except:
        return False


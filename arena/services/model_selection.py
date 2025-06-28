"""
Model selection service for weighted random model selection.
"""

import random
from models import Model, ModelType
from config import SMOOTHING_FACTOR_MODEL_SELECTION


def get_weighted_random_models(
    applicable_models: list[Model], num_to_select: int, model_type: ModelType
) -> list[Model]:
    """
    Select models using weighted random selection based on ELO ratings.
    
    Models with lower ELO ratings get higher selection weights to encourage
    more balanced comparisons and faster convergence.
    """
    if len(applicable_models) <= num_to_select:
        return applicable_models

    # Calculate weights based on inverse ELO (lower ELO = higher weight)
    weights = []
    max_elo = max(model.current_elo for model in applicable_models)
    min_elo = min(model.current_elo for model in applicable_models)
    
    # Normalize ELO ratings to [0, 1] range
    elo_range = max_elo - min_elo if max_elo > min_elo else 1
    
    for model in applicable_models:
        # Normalize ELO to [0, 1]
        normalized_elo = (model.current_elo - min_elo) / elo_range
        
        # Calculate weight (lower ELO = higher weight)
        # Use smoothing factor to control how much ELO affects selection probability
        weight = 1 / (1 + normalized_elo * SMOOTHING_FACTOR_MODEL_SELECTION)
        weights.append(weight)

    # Select models using weighted random selection
    selected_models = []
    remaining_models = applicable_models.copy()
    remaining_weights = weights.copy()
    
    for _ in range(num_to_select):
        # Choose a model based on weights
        selected_model = random.choices(remaining_models, weights=remaining_weights)[0]
        selected_models.append(selected_model)
        
        # Remove selected model from remaining options
        index = remaining_models.index(selected_model)
        remaining_models.pop(index)
        remaining_weights.pop(index)
        
        if not remaining_models:
            break
    
    return selected_models 
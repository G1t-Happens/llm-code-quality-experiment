package com.llmquality.faulty.service.interfaces;

import com.llmquality.faulty.exception.ResourceAlreadyExistsException;
import com.llmquality.faulty.exception.ResourceNotFoundException;

import java.util.List;


/**
 * Generic CRUD interface with standard type parameter naming conventions:
 * <ul>
 *     <li>R: Request / Input DTO type</li>
 *     <li>S: Response / Output DTO type</li>
 * </ul>
 *
 * @param <R> the type of the DTO used for create/update requests
 * @param <S> the type of the DTO returned in responses without sensitive data
 */
public interface CRUDable<R, S> {

    /**
     * Retrieves all entities as response DTOs.
     *
     * @return a list of all entities represented as response DTOs
     */
    List<S> listAll();

    /**
     * Retrieves an entity by its unique identifier.
     *
     * @param id the ID of the entity to retrieve
     * @return the entity represented as a response DTO
     * @throws ResourceNotFoundException if no entity with the specified ID is found
     */
    S getById(Long id) throws ResourceNotFoundException;

    /**
     * Saves a new entity from a request DTO.
     *
     * @param requestDTO the DTO containing data to create the entity
     * @return the saved entity represented as a response DTO
     * @throws ResourceAlreadyExistsException if an entity with the same unique identifier already exists
     */
    S save(R requestDTO) throws ResourceAlreadyExistsException;

    /**
     * Updates an existing entity by ID using a request DTO.
     *
     * @param id         the ID of the entity to update
     * @param requestDTO the DTO containing updated data
     * @return the updated entity represented as a response DTO
     * @throws ResourceNotFoundException if the entity with the given ID does not exist
     */
    S update(Long id, R requestDTO) throws ResourceNotFoundException;

    /**
     * Deletes an entity by its unique identifier.
     *
     * @param id the ID of the entity to delete
     * @throws ResourceNotFoundException if no entity with the specified ID exists
     */
    void delete(Long id) throws ResourceNotFoundException;
}
